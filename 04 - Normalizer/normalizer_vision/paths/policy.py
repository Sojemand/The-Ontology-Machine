"""Runtime path policy for the self-contained Normalizer module."""
from __future__ import annotations

from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent.parent


def module_root() -> Path:
    return MODULE_ROOT


def state_dir(root: Path | None = None) -> Path:
    return (root or MODULE_ROOT) / "state"


def log_dir(root: Path | None = None) -> Path:
    return state_dir(root) / "logs"
