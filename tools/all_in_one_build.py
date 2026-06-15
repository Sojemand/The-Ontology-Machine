from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from installer_stage import find_iscc
from all_in_one_config import (
    CLIENT_FRONTEND_MODULE,
    MODULE_DIRS,
    PIPELINE_ROOT,
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


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ensure_module_runtime(module_name: str) -> None:
    module_root = PIPELINE_ROOT / module_name
    if module_name == CLIENT_FRONTEND_MODULE:
        required_paths = (module_root / "node" / "node.exe", module_root / "app" / "index.html", module_root / "runtime" / "launch-server.bat")
    else:
        required_paths = (module_root / "runtime" / "python" / "python.exe", module_root / "runtime" / "runtime-manifest.json")
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Runtime artifacts missing for {module_name}. Run tools\\build-runtimes.py first. Missing: {missing}")


def run_runtime_build(*, source_python: str | None) -> None:
    command = [sys.executable, str(build_runtimes_script()), "--offline"]
    if source_python:
        command.extend(["--python", source_python])
    run(command, cwd=PIPELINE_ROOT)


def compile_installer(stage_dir: Path, output_dir: Path, *, app_version: str) -> Path:
    script_path = installer_script()
    if not script_path.exists():
        raise FileNotFoundError(f"Inno setup script missing: {script_path}")
    iscc = find_iscc(PIPELINE_ROOT)
    if iscc is None:
        raise FileNotFoundError("ISCC.exe was not found. Install Inno Setup 6 first.")
    output_dir.mkdir(parents=True, exist_ok=True)
    run([str(iscc), f"/DSourceDir={stage_dir}", f"/DOutputDir={output_dir}", f"/DAppVersion={app_version}", str(script_path)], cwd=PIPELINE_ROOT)
    return output_dir


def build_all_in_one(*, app_version: str, skip_runtime_build: bool, source_python: str | None, compile: bool) -> Path:
    if not skip_runtime_build:
        run_runtime_build(source_python=source_python)
    for module_name in MODULE_DIRS:
        ensure_module_runtime(module_name)
    stage_dir = default_stage_dir()
    reset_stage_dir(stage_dir)
    for module_name in MODULE_DIRS:
        print(f"[STAGE] {module_name}")
        stage_module(module_name, stage_dir)
    stage_root_payloads(stage_dir)
    copy_installer_icons(stage_dir)
    write_root_launchers(stage_dir)
    write_release_manifest(stage_dir, app_version=app_version)
    print(f"[STAGE] {stage_dir}")
    if compile:
        output_dir = compile_installer(stage_dir, default_output_dir(), app_version=app_version)
        print(f"[INSTALLER] {output_dir}")
        return output_dir
    print("[INSTALLER] Kompilierung uebersprungen (--compile nicht gesetzt)")
    return stage_dir
