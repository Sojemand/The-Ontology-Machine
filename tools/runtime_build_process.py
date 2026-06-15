from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def portable_runtime_env(runtime_dir: Path) -> dict[str, str]:
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHOME": str(runtime_dir),
        "PYTHONPATH": "",
    }
    tcl_dir = runtime_dir / "tcl"
    if (tcl_dir / "tcl8.6").exists():
        env["TCL_LIBRARY"] = (tcl_dir / "tcl8.6").as_posix()
    if (tcl_dir / "tk8.6").exists():
        env["TK_LIBRARY"] = (tcl_dir / "tk8.6").as_posix()
    return env
