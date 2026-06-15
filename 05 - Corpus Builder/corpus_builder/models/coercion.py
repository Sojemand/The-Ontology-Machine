"""Private scalar coercion helpers for config loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value) if value in {0, 1} else default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _coerce_int(value: Any, default: int, *, minimum: int | None = None) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and normalized < minimum:
        return default
    return normalized


def _coerce_text(value: Any, default: str) -> str:
    if isinstance(value, Path):
        return str(value)
    if not isinstance(value, str):
        return default
    text = value.strip()
    return text or default


def _coerce_mode(value: Any, default: str) -> str:
    mode = _coerce_text(value, default).lower()
    return mode if mode in {"api", "local"} else default
