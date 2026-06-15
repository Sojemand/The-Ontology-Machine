from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MODULE_ROOT = Path(__file__).parent.parent.parent
PIPELINE_ROOT = MODULE_ROOT.parent
TEST_DATA = Path(__file__).parent / "test_data"
RUNTIME_ROOT = MODULE_ROOT / "runtime" / "python"
RUNTIME_PYTHON = RUNTIME_ROOT / "python.exe"
CHECK_RUNTIME = MODULE_ROOT / "check-runtime.bat"
INSTALLER = MODULE_ROOT / "installer.bat"
BUILD_INSTALLER = MODULE_ROOT / "build-installer.bat"
BUILD_RUNTIME_PS1 = MODULE_ROOT / "tools" / "build-runtime.ps1"
INSTALLER_ISS = MODULE_ROOT / "installer" / "ValidatorVision.iss"
ROOT_BUILD_INSTALLER = PIPELINE_ROOT / "tools" / "build-installer.py"
RUNTIME_MANIFEST = MODULE_ROOT / "runtime" / "runtime-manifest.json"
MODULE_MANIFEST = MODULE_ROOT / "module-manifest.json"
STAGE_ROOT = MODULE_ROOT / "dist" / "stage"


def _run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def _run_batch(script: Path, *arguments: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run_command(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd, env=env)


def _stage_bundle() -> Path:
    completed = _run_command(
        [
            sys.executable,
            str(ROOT_BUILD_INSTALLER),
            "--module",
            "03 - Validator",
            "--skip-runtime-build",
            "--app-version",
            "2099-01-01",
        ],
        cwd=PIPELINE_ROOT,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return STAGE_ROOT
