from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from installer_config import load_installer_config
from installer_stage import compile_installer, copy_release_tree, write_release_manifest

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODULE_NAME = "05 - Corpus Builder"


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _default_app_version() -> str:
    return date.today().isoformat()


def _module_root(module_name: str) -> Path:
    return PIPELINE_ROOT / module_name


def _staging_dir(module_root: Path) -> Path:
    return module_root / "dist" / "stage"


def _installer_output_dir(module_root: Path) -> Path:
    return module_root / "dist" / "installer"


def _build_runtimes_script() -> Path:
    return SCRIPT_DIR / "build-runtimes.py"


def _ensure_runtime_exists(module_root: Path) -> None:
    runtime_python = module_root / "runtime" / "python" / "python.exe"
    if not runtime_python.exists():
        raise FileNotFoundError(f"Runtime fehlt: {runtime_python}")


def _run_runtime_build(module_name: str, *, source_python: str | None) -> None:
    command = [sys.executable, str(_build_runtimes_script()), "--module", module_name, "--offline"]
    if source_python:
        command.extend(["--python", source_python])
    _run(command, cwd=PIPELINE_ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage and optionally compile a Vision Pipeline module installer.")
    parser.add_argument("--module", default=DEFAULT_MODULE_NAME)
    parser.add_argument("--source-python", default=None, help="Optional CPython 3.11 x64 executable for runtime rebuilds.")
    parser.add_argument("--app-version", default=_default_app_version())
    parser.add_argument(
        "--skip-runtime-build",
        action="store_true",
        help="Reuse the existing runtime instead of rebuilding it first.",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Compile the .iss script with Inno Setup after staging.",
    )
    args = parser.parse_args(argv)

    module_root = _module_root(args.module)
    if not module_root.exists():
        raise FileNotFoundError(f"Modulordner nicht gefunden: {module_root}")
    installer_config = load_installer_config(module_root)

    if not args.skip_runtime_build:
        _run_runtime_build(args.module, source_python=args.source_python)

    _ensure_runtime_exists(module_root)
    staging_dir = _staging_dir(module_root)
    output_dir = _installer_output_dir(module_root)
    copy_release_tree(
        module_root,
        staging_dir,
        mutable_dirs=installer_config.mutable_dirs,
        mutable_files=installer_config.mutable_files,
        excluded_runtime_paths=installer_config.excluded_runtime_paths,
    )
    write_release_manifest(
        module_root,
        staging_dir,
        app_version=args.app_version,
        mutable_dirs=installer_config.mutable_dirs,
        mutable_files=installer_config.mutable_files,
        excluded_runtime_paths=installer_config.excluded_runtime_paths,
        sign_targets=installer_config.sign_targets,
    )

    print(f"[STAGE] {staging_dir}")
    if args.compile:
        compiled_dir = compile_installer(
            PIPELINE_ROOT,
            module_root,
            staging_dir,
            output_dir,
            app_version=args.app_version,
            script_name=installer_config.script_name,
        )
        print(f"[INSTALLER] {compiled_dir}")
    else:
        print("[INSTALLER] Kompilierung uebersprungen (--compile nicht gesetzt)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
