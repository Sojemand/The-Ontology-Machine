"""Hard validation for Edit Suite bootstrap paths."""

from __future__ import annotations

from pathlib import Path

from .types import StartupPrerequisiteError


def require_directory(path: Path, *, label: str) -> Path:
    if not path.exists():
        raise StartupPrerequisiteError(f"{label} is missing: {path}")
    if not path.is_dir():
        raise StartupPrerequisiteError(f"{label} must be a directory: {path}")
    return path.resolve()


def require_file(path: Path, *, label: str) -> Path:
    if not path.exists():
        raise StartupPrerequisiteError(f"{label} is missing: {path}")
    if not path.is_file():
        raise StartupPrerequisiteError(f"{label} must be a file: {path}")
    return path.resolve()
