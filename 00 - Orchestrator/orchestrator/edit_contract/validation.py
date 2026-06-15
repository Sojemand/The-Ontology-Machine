"""Hard validation for orchestrator edit-contract payloads."""

from __future__ import annotations

from typing import Any

from .types import (
    DESCRIBE_SURFACES_ACTION,
    READ_BUNDLE_ACTION,
    READ_SURFACE_ACTION,
    SURFACE_IDS,
    VALIDATE_SURFACE_ACTION,
    WRITE_SURFACE_ACTION,
)


def require_action(payload: dict[str, Any]) -> str:
    value = payload.get("action")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("action is missing or invalid.")
    action = value.strip()
    if action in {DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION}:
        return action
    raise ValueError(f"Unknown action: {action}")


def require_surface_id(payload: dict[str, Any]) -> str:
    value = payload.get("surface_id")
    if not isinstance(value, str) or value.strip() not in SURFACE_IDS:
        raise ValueError("surface_id is missing or invalid.")
    return value.strip()


def require_surface_value(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("value")
    if not isinstance(value, dict):
        raise ValueError("value must be a JSON object.")
    return value
