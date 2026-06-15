"""Validation helpers for edit-contract requests."""
from __future__ import annotations

from .types import DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, SURFACE_IDS, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION


def require_action(payload: dict) -> str:
    action = str(payload.get("action", "")).strip()
    if not action:
        raise ValueError("Aktion fehlt.")
    if action not in {DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION}:
        raise ValueError(f"Unbekannte Aktion: {action}")
    return action


def require_surface_id(payload: dict) -> str:
    surface_id = str(payload.get("surface_id", "")).strip()
    if surface_id not in SURFACE_IDS:
        raise ValueError(f"Unbekannte Surface: {surface_id}")
    return surface_id


def require_surface_value(payload: dict) -> dict:
    value = payload.get("value")
    if not isinstance(value, dict):
        raise ValueError("value muss ein JSON-Objekt sein.")
    return value
