"""Field value normalization helpers for loader persistence."""

from __future__ import annotations

from typing import Any


def extracted_field_values(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, dict):
        return ()
    if isinstance(value, list):
        return tuple(item for item in value if item is not None and not isinstance(item, (dict, list)))
    return (value,)


__all__ = ["extracted_field_values"]
