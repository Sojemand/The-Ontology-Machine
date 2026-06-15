from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from semantic_control_kernel.bootstrap.runtime_report_checks import (
    check as _check,
    first_error as _first_error,
    manifest_check as _manifest_check,
    package_import_check as _package_import_check,
    runtime_manifest_check as _runtime_manifest_check,
    runtime_paths_check as _runtime_paths_check,
    runtime_python as _runtime_python,
    sibling_path_leaks as _sibling_path_leaks,
    state_probe as _state_probe,
)
from semantic_control_kernel.bootstrap.runtime_report_constants import (
    MODULE_KEY,
    REQUIRED_ACTION_COUNT,
    REQUIRED_CONTRACT_VERSION,
    REQUIRED_MANIFEST_STATUS,
)
from semantic_control_kernel.bootstrap.runtime_report_imports import contract_import_check as _contract_import_check
from semantic_control_kernel.bootstrap.runtime_report_paths import is_relative_to as _is_relative_to


def build_report(
    root: str | Path,
    *,
    strict: bool = False,
    sys_path: list[str] | None = None,
    cwd: str | Path | None = None,
) -> dict[str, object]:
    module_root = Path(root).resolve()
    runtime_root = module_root / "runtime" / "python"
    runtime_python = _runtime_python(runtime_root)
    effective_sys_path = list(sys.path if sys_path is None else sys_path)
    effective_cwd = Path(os.getcwd() if cwd is None else cwd).resolve()
    checks: list[dict[str, object]] = []

    checks.append(_check("runtime_python_exists", runtime_python.exists(), code="runtime_missing", message="Runtime Python is missing."))
    if runtime_python.exists():
        paths_ok, paths_message = _runtime_paths_check(runtime_root)
        checks.append(_check("runtime_stdlib_paths", paths_ok, code="runtime_layout_invalid", message=paths_message))
        pyvenv_path = runtime_root / "pyvenv.cfg"
        checks.append(
            _check(
                "runtime_has_no_pyvenv_cfg",
                not pyvenv_path.exists(),
                code="runtime_layout_invalid",
                message=f"pyvenv.cfg must be absent from {runtime_root}.",
            )
        )

    manifest_ok, manifest_message, manifest_status, contract_version = _manifest_check(module_root)
    checks.append(_check("module_manifest", manifest_ok, code="manifest_invalid", message=manifest_message))
    runtime_manifest_ok, runtime_manifest_message = _runtime_manifest_check(module_root)
    checks.append(_check("runtime_manifest", runtime_manifest_ok, code="runtime_manifest_invalid", message=runtime_manifest_message))
    import_ok, import_message = _package_import_check(module_root, effective_sys_path)
    checks.append(_check("package_import_path", import_ok, code="package_import_path_invalid", message=import_message))

    leaks = _sibling_path_leaks(module_root, effective_sys_path)
    checks.append(_check("no_sibling_module_sys_path", not leaks, code="sibling_path_leak", message="Sibling module paths are present in sys.path: " + ", ".join(leaks)))
    state_ok, state_message = _state_probe(module_root)
    checks.append(_check("state_write_probe", state_ok, code="state_write_failed", message=state_message))
    checks.append(_check("working_directory_is_module_root", effective_cwd == module_root, code="working_directory_invalid", message=f"Working directory must be module root: {module_root}"))
    contract_ok, contract_message = _contract_import_check(module_root, effective_sys_path)
    checks.append(_check("contract_import_no_side_effects", contract_ok, code="contract_import_failed", message=contract_message))

    error = _first_error(checks)
    report: dict[str, object] = {
        "ok": error is None,
        "status": "ok" if error is None else "error",
        "module_key": MODULE_KEY,
        "module_root": str(module_root),
        "runtime_root": str(runtime_root),
        "runtime_python": str(runtime_python),
        "manifest_status": manifest_status,
        "contract_version": contract_version,
        "checks": checks,
    }
    if error is not None:
        report["error"] = error
    if not strict and error is not None:
        report["strict"] = False
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the Semantic Control Kernel runtime preflight report.")
    parser.add_argument("--root", required=True, help="Semantic Control Kernel module root.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any check fails.")
    args = parser.parse_args(argv)

    report = build_report(args.root, strict=args.strict)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["ok"] or not args.strict else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
