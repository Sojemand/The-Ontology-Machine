from __future__ import annotations

import importlib.machinery
import json
import sys
import sysconfig
from pathlib import Path
from typing import Iterable

from semantic_control_kernel.bootstrap.runtime_report_constants import (
    MODULE_KEY,
    REQUIRED_ACTION_COUNT,
    REQUIRED_CONTRACT_VERSION,
    REQUIRED_MANIFEST_STATUS,
)
from semantic_control_kernel.bootstrap.runtime_report_paths import is_relative_to, runtime_python


def json_file(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def check(name: str, ok: bool, *, code: str | None = None, message: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"name": name, "ok": ok}
    if not ok:
        payload["code"] = code or name
        payload["message"] = message or code or name
    return payload


def first_error(checks: Iterable[dict[str, object]]) -> dict[str, object] | None:
    for item in checks:
        if not item.get("ok"):
            return {
                "code": str(item.get("code") or item.get("name") or "runtime_preflight_failed"),
                "message": str(item.get("message") or "Runtime preflight failed."),
            }
    return None


def runtime_paths_check(runtime_root: Path) -> tuple[bool, str]:
    missing = [str(path) for path in required_runtime_files(runtime_root) if not path.exists()]
    if missing:
        return False, "Missing runtime stdlib paths: " + ", ".join(missing)

    executable = Path(sys.executable)
    if not is_relative_to(executable, runtime_root):
        return True, "Runtime file layout exists; sysconfig path check is skipped outside runtime Python."

    leaking = []
    for key in ("stdlib", "platstdlib", "purelib", "scripts"):
        value = sysconfig.get_path(key)
        if value and not is_relative_to(Path(value).resolve(), runtime_root):
            leaking.append(f"{key}={value}")
    if leaking:
        return False, "Runtime sysconfig paths leave runtime/python: " + ", ".join(leaking)
    return True, "Runtime stdlib paths resolve under runtime/python."


def manifest_check(module_root: Path) -> tuple[bool, str, str | None, int | None]:
    try:
        manifest = json_file(module_root / "module-manifest.json")
    except Exception as exc:
        return False, f"module-manifest.json is invalid: {exc}", None, None
    status = manifest.get("status")
    contract_version = manifest.get("contract_version")
    actions = manifest.get("actions")
    if (
        manifest.get("module_key") != MODULE_KEY
        or status != REQUIRED_MANIFEST_STATUS
        or contract_version != REQUIRED_CONTRACT_VERSION
        or not isinstance(actions, list)
        or len(actions) != REQUIRED_ACTION_COUNT
    ):
        return False, "module-manifest.json does not match the active runtime contract surface.", str(status), None
    return True, "module-manifest.json matches the active runtime contract surface.", str(status), int(contract_version)


def runtime_manifest_check(module_root: Path) -> tuple[bool, str]:
    try:
        manifest = json_file(module_root / "runtime" / "runtime-manifest.json")
    except Exception as exc:
        return False, f"runtime/runtime-manifest.json is invalid: {exc}"
    expected = {
        "module_key": MODULE_KEY,
        "status": REQUIRED_MANIFEST_STATUS,
        "contract_version": REQUIRED_CONTRACT_VERSION,
        "runtime_kind": "python",
        "runtime_path": "runtime/python",
        "python_version": "3.11",
        "build_status": "buildable",
        "normal_operation_requires_host_python": False,
        "runtime_builder": "root_tools_build_runtimes",
        "runtime_check_module": "semantic_control_kernel.bootstrap.runtime_report",
    }
    for key, expected_value in expected.items():
        if manifest.get(key) != expected_value:
            return False, f"runtime manifest field {key!r} is not {expected_value!r}."
    return True, "runtime/runtime-manifest.json matches the active runtime contract surface."


def package_import_check(module_root: Path, sys_path: list[str]) -> tuple[bool, str]:
    spec = importlib.machinery.PathFinder.find_spec(MODULE_KEY, sys_path)
    if spec is None or spec.origin is None:
        return False, "semantic_control_kernel package cannot be resolved."
    origin = Path(spec.origin).resolve()
    expected_root = module_root / MODULE_KEY
    if not is_relative_to(origin, expected_root):
        return False, f"semantic_control_kernel resolves outside module root: {origin}"
    return True, "semantic_control_kernel resolves from this module root."


def sibling_path_leaks(module_root: Path, sys_path: list[str]) -> list[str]:
    pipeline_root = module_root.parent.resolve()
    siblings = [child.resolve() for child in pipeline_root.iterdir() if child.is_dir() and child.resolve() != module_root.resolve()]
    leaks: list[str] = []
    for raw_entry in sys_path:
        if not raw_entry:
            continue
        try:
            entry = Path(raw_entry).resolve()
        except OSError:
            continue
        if entry == pipeline_root or any(entry == sibling or is_relative_to(entry, sibling) for sibling in siblings):
            leaks.append(str(entry))
    return leaks


def state_probe(module_root: Path) -> tuple[bool, str]:
    state_root = module_root / "state"
    if not state_root.exists() or not state_root.is_dir():
        return False, "state/ does not exist."
    probe = state_root / ".runtime_write_probe.tmp"
    try:
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        return False, f"state/ write probe failed: {exc}"
    return True, "state/ write probe succeeded and cleaned up."


def required_runtime_files(runtime_root: Path) -> tuple[Path, ...]:
    return (
        runtime_root / "Lib" / "os.py",
        runtime_root / "Lib" / "encodings" / "__init__.py",
        runtime_root / "Lib" / "site-packages",
    )
