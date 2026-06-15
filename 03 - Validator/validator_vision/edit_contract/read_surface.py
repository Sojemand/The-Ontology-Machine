"""Read operations for validator edit-contract surfaces."""
from __future__ import annotations

from . import repository
from .types import DEBUG_CAPABILITIES_SURFACE_ID, REPORT_POLICY_SURFACE_ID, SETTINGS_SURFACE_ID


def read_surface(surface_id: str, *, home_root, module_root) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        return repository.read_settings(home_root)
    if surface_id == REPORT_POLICY_SURFACE_ID:
        return repository.read_report_preview_policy(home_root)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        return repository.read_debug_capabilities(module_root)
    raise ValueError(f"Unbekannte Surface: {surface_id}")
