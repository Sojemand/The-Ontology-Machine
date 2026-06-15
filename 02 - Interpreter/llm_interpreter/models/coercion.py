"""Low-level coercion helpers for environment-backed config values."""
from __future__ import annotations

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def coerce_bool(value: object, default: bool, *, field: str = "value") -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        raise ValueError(f"{field} muss true/false sein.")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    raise ValueError(f"{field} muss true/false sein.")


def parse_env_int(value: object, default: int, *, field: str = "value") -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field} muss eine Ganzzahl sein.")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} muss eine Ganzzahl sein.") from None
