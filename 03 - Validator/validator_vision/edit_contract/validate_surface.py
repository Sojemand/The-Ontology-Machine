"""Validation entrypoints for validator edit-contract surfaces."""
from __future__ import annotations

from . import validation
from .types import DEBUG_CAPABILITIES_SURFACE_ID, REPORT_POLICY_SURFACE_ID, SETTINGS_SURFACE_ID


def validate_surface(surface_id: str, value: dict) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        return validation.validate_settings_payload(value)
    if surface_id == REPORT_POLICY_SURFACE_ID:
        return validation.validate_report_policy_payload(value)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("validator.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
