from __future__ import annotations

from pathlib import Path


def runtime_python(runtime_root: Path) -> Path:
    candidates = (
        runtime_root / "python.exe",
        runtime_root / "Scripts" / "python.exe",
        runtime_root / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
