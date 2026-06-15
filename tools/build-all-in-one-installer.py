from __future__ import annotations

import argparse
from pathlib import Path

from all_in_one_build import build_all_in_one, compile_installer, ensure_module_runtime, run, run_runtime_build
from all_in_one_config import (
    DEFAULT_APP_VERSION,
    DEFAULT_DEMO_DB_PATH,
    MODULE_DIRS,
    PIPELINE_ROOT,
    ROOT_PAYLOAD_DIRS,
    build_runtimes_script,
    default_output_dir,
    default_stage_dir,
    installer_script,
)
from all_in_one_stage import (
    copy_installer_icons,
    reset_stage_dir,
    stage_module,
    stage_root_payloads,
    write_release_manifest,
    write_root_launchers,
)
from all_in_one_texts import check_all_runtimes_batch, root_readme, uninstall_launcher_batch, uninstall_powershell


def _run(command: list[str], *, cwd: Path):
    return run(command, cwd=cwd)


def _default_stage_dir() -> Path:
    return default_stage_dir()


def _default_output_dir() -> Path:
    return default_output_dir()


def _installer_script() -> Path:
    return installer_script()


def _build_runtimes_script() -> Path:
    return build_runtimes_script()


def _ensure_module_runtime(module_name: str) -> None:
    ensure_module_runtime(module_name)


def _run_runtime_build(*, source_python: str | None) -> None:
    run_runtime_build(source_python=source_python)


def _reset_stage_dir(stage_dir: Path) -> None:
    reset_stage_dir(stage_dir)


def _stage_module(module_name: str, stage_dir: Path) -> None:
    stage_module(module_name, stage_dir)


def _stage_root_payloads(stage_dir: Path) -> None:
    stage_root_payloads(stage_dir)


def _copy_installer_icons(stage_dir: Path) -> None:
    copy_installer_icons(stage_dir)


def _write_root_launchers(stage_dir: Path) -> None:
    write_root_launchers(stage_dir)


def _check_all_runtimes_batch() -> str:
    return check_all_runtimes_batch()


def _uninstall_launcher_batch() -> str:
    return uninstall_launcher_batch()


def _uninstall_powershell() -> str:
    return uninstall_powershell()


def _root_readme() -> str:
    return root_readme()


def _write_release_manifest(stage_dir: Path, *, app_version: str) -> None:
    write_release_manifest(stage_dir, app_version=app_version)


def _compile_installer(stage_dir: Path, output_dir: Path, *, app_version: str) -> Path:
    return compile_installer(stage_dir, output_dir, app_version=app_version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage and compile the Ontology Machine all-in-one installer.")
    parser.add_argument("--app-version", default=DEFAULT_APP_VERSION)
    parser.add_argument("--source-python", default=None, help="Optional CPython 3.11 x64 executable for runtime rebuilds.")
    parser.add_argument("--skip-runtime-build", action="store_true", help="Reuse existing bundled runtimes instead of rebuilding them first.")
    parser.add_argument("--compile", action="store_true", help="Compile the staged payload with Inno Setup.")
    args = parser.parse_args(argv)
    build_all_in_one(app_version=args.app_version, skip_runtime_build=args.skip_runtime_build, source_python=args.source_python, compile=args.compile)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
