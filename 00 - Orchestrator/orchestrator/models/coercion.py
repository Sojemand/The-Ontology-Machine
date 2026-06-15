"""Best-effort coercion helpers for persisted orchestrator data."""

from __future__ import annotations

from typing import Any


def coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def coerce_int(value: Any, default: int = 0, *, minimum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    return result


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
        return default
    return bool(value)


def coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            text = coerce_str(item).strip()
            if text:
                result.append(text)
        return result
    text = coerce_str(value).strip()
    return [text] if text else []
