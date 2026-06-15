"""Write operations for validator edit-contract surfaces."""
from __future__ import annotations

from . import repository
from .types import DEBUG_CAPABILITIES_SURFACE_ID, REPORT_POLICY_SURFACE_ID, SETTINGS_SURFACE_ID


def write_surface(surface_id: str, value: dict, *, home_root) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        return repository.write_settings(home_root, value)
    if surface_id == REPORT_POLICY_SURFACE_ID:
        return repository.write_report_preview_policy(home_root, value)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("validator.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
