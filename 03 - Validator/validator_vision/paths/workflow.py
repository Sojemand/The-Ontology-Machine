"""Workflow stage for fallback-aware runtime path setup."""
from __future__ import annotations

from pathlib import Path

from . import repository
from .policy import _build_layout


def ensure_app_layout(root: Path | None = None) -> Path:
    return repository.ensure_app_layout(_build_layout(root))
