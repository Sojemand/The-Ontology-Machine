"""Runtime-manifest checks for the MCP Server module."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .contract_client import _runtime_python


def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_runtime_manifest(*, strict_executable: bool = False) -> dict[str, Any]:
    root = module_root()
    manifest_path = root / "runtime" / "runtime-manifest.json"
    runtime_dir = root / "runtime" / "python"
    python_executable = _runtime_python(runtime_dir)
    if not manifest_path.exists():
        return _result(root, manifest_path, runtime_dir, python_executable=python_executable, strict_executable=strict_executable, missing=["runtime/runtime-manifest.json"])

    try:
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return _result(root, manifest_path, runtime_dir, python_executable=python_executable, strict_executable=strict_executable, errors=[f"runtime-manifest.json ist ungueltig: {exc}"])

    required = [str(item) for item in manifest.get("required_files", []) if str(item).strip()]
    missing = [relative for relative in required if not (root / relative).exists()]
    errors: list[str] = []
    if strict_executable and not _is_within(Path(sys.executable).resolve(), runtime_dir.resolve()):
        errors.append(f"Healthcheck laeuft nicht aus der gebuendelten Runtime: {sys.executable}")
    if strict_executable and not python_executable.exists():
        errors.append(f"Gebuendelte Python-Runtime fehlt: {python_executable}")
    return _result(root, manifest_path, runtime_dir, python_executable=python_executable, strict_executable=strict_executable, missing=missing, errors=errors)


def _result(
    root: Path,
    manifest_path: Path,
    runtime_dir: Path,
    *,
    python_executable: Path,
    strict_executable: bool,
    missing: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    missing = missing or []
    errors = errors or []
    ok = not missing and not errors
    return {
        "ok": ok,
        "module_root": str(root),
        "manifest_path": str(manifest_path),
        "runtime_dir": str(runtime_dir),
        "python_executable": sys.executable,
        "bundled_python_expected": str(python_executable),
        "strict_executable": strict_executable,
        "self_contained_runtime": _is_within(Path(sys.executable).resolve(), runtime_dir.resolve()),
        "missing_required_files": missing,
        "errors": errors,
    }


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
