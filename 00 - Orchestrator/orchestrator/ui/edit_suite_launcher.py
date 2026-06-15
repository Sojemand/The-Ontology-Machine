"""Launch helpers for the sibling Edit Suite desktop app."""

from __future__ import annotations

import os
from pathlib import Path

_EDIT_SUITE_DIRNAME = "06 - Edit Suite"
_RUN_BATCH_NAME = "run.bat"


def run_script_path(project_root: Path) -> Path:
    project_root = Path(project_root).resolve()
    script_path = project_root.parent / _EDIT_SUITE_DIRNAME / _RUN_BATCH_NAME
    if not script_path.exists():
        raise FileNotFoundError(f"Edit Suite launcher is missing: {script_path}")
    return script_path


def launch(project_root: Path) -> Path:
    script_path = run_script_path(project_root)
    try:
        os.startfile(str(script_path))  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise RuntimeError("Edit Suite launch is not supported on this system.") from exc
    return script_path
