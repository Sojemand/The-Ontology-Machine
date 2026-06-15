"""Nested payload helpers shared by structured editors."""
from __future__ import annotations


def get_nested(payload: dict, field_path: str):
    current = payload
    for key in field_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def set_nested(payload: dict, field_path: str, value) -> None:
    keys = field_path.split(".")
    current = payload
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value

