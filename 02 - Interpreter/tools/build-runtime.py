from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_MANIFEST = PROJECT_ROOT / "module-manifest.json"
RUNTIME_MANIFEST = PROJECT_ROOT / "runtime" / "runtime-manifest.json"
RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "python"
HEADLESS_RUNTIME_PATHS = (
    Path("tcl"),
    Path("DLLs") / "tcl86t.dll",
    Path("DLLs") / "tk86t.dll",
    Path("DLLs") / "_tkinter.pyd",
    Path("Lib") / "tkinter",
    Path("Lib") / "idlelib",
    Path("Lib") / "turtledemo",
    Path("Lib") / "ensurepip",
    Path("Scripts"),
)


def _launcher_package_name() -> str:
    payload = json.loads(MODULE_MANIFEST.read_text(encoding="utf-8"))
    package_name = str(payload.get("launcher_module") or "").strip()
    if not package_name:
        raise ValueError(f"launcher_module fehlt in {MODULE_MANIFEST}")
    return package_name


def _remove_path(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
        return
    target.unlink(missing_ok=True)


def _finalize_runtime_layout(runtime_root: Path) -> None:
    if not runtime_root.exists():
        return
    for relative_path in HEADLESS_RUNTIME_PATHS:
        _remove_path(runtime_root / relative_path)


def _runtime_manifest_payload(package_name: str) -> dict[str, object]:
    return {
        "python_version": "3.11",
        "runtime_candidates": {
            "python": [
                "runtime/python/python.exe",
                "runtime/python/Scripts/python.exe",
                "runtime/python/bin/python",
            ]
        },
        "required_files": [
            "runtime/python/python.exe",
            "runtime/python/pythonw.exe",
            "runtime/python/python3.dll",
            "runtime/python/python311.dll",
            "runtime/python/vcruntime140.dll",
            "runtime/python/vcruntime140_1.dll",
            "runtime/python/Lib/encodings/__init__.py",
            "runtime/requirements.lock.txt",
            f"{package_name}/config_bootstrap.py",
            f"{package_name}/orchestrator_contract/__main__.py",
            f"{package_name}/orchestrator_contract/adapter.py",
            f"{package_name}/orchestrator_contract/debug_processing.py",
            f"{package_name}/orchestrator_contract/debug_support.py",
            f"{package_name}/orchestrator_contract/types.py",
            f"{package_name}/orchestrator_contract/validation.py",
            f"{package_name}/orchestrator_contract/workflow.py",
            f"{package_name}/edit_contract/__main__.py",
            f"{package_name}/edit_contract/__init__.py",
            f"{package_name}/edit_contract/describe_surfaces.py",
            f"{package_name}/edit_contract/env_repository.py",
            f"{package_name}/edit_contract/files.py",
            f"{package_name}/edit_contract/prompt_repository.py",
            f"{package_name}/edit_contract/read_surface.py",
            f"{package_name}/edit_contract/repository.py",
            f"{package_name}/edit_contract/summary.py",
            f"{package_name}/edit_contract/types.py",
            f"{package_name}/edit_contract/validate_surface.py",
            f"{package_name}/edit_contract/validation.py",
            f"{package_name}/edit_contract/workflow.py",
            f"{package_name}/edit_contract/write_surface.py",
            f"{package_name}/interpreter/adapter.py",
            f"{package_name}/interpreter/persisted_validation.py",
            f"{package_name}/interpreter/results.py",
            f"{package_name}/prompts/schema.py",
            f"{package_name}/runtime_paths.py",
            f"{package_name}/runtime_support.py",
            "module-manifest.json",
            "check-runtime.bat",
            "tools/check-runtime.ps1",
            ".env.example",
        ],
    }


def _write_runtime_manifest() -> None:
    _finalize_runtime_layout(RUNTIME_ROOT)
    payload = _runtime_manifest_payload(_launcher_package_name())
    RUNTIME_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize the bundled Interpreter runtime.")
    parser.add_argument(
        "--write-runtime-manifest",
        action="store_true",
        help="Prune GUI-only runtime artefacts and rewrite runtime/runtime-manifest.json.",
    )
    args = parser.parse_args(argv)

    if args.write_runtime_manifest:
        _write_runtime_manifest()
        return 0

    _write_runtime_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
