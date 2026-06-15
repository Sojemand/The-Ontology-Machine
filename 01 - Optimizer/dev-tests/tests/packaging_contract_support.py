"""Shared process helpers for packaging/runtime contract tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
DIST_ROOT = MODULE_ROOT / "dist"
STAGE_ROOT = DIST_ROOT / "stage"
RUNTIME_ROOT = MODULE_ROOT / "runtime" / "python"
RUNTIME_PYTHON = RUNTIME_ROOT / "python.exe"
CHECK_RUNTIME = MODULE_ROOT / "check-runtime.bat"
INSTALLER = MODULE_ROOT / "installer.bat"
BUILD_INSTALLER = MODULE_ROOT / "build-installer.bat"
RUNTIME_MANIFEST = MODULE_ROOT / "runtime" / "runtime-manifest.json"
MODULE_MANIFEST = MODULE_ROOT / "module-manifest.json"


def run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def run_batch(script: Path, *arguments: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_command(["cmd.exe", "/c", "call", str(script), *arguments], cwd=cwd, env=env)
