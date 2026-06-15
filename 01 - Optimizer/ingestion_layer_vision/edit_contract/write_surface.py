"""Write operations for edit-contract surfaces."""
from __future__ import annotations

from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    OCR_PROMPT_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)


def write_surface(surface_id: str, value: dict, *, layout) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        from . import settings_repository

        return settings_repository.write_settings(layout, value)
    if surface_id == OCR_PROMPT_SURFACE_ID:
        from . import prompt_repository

        return prompt_repository.write_ocr_prompt(layout, value)
    if surface_id == OUTPUT_CONTRACT_PREVIEW_SURFACE_ID:
        raise ValueError("optimizer.output_contract_preview ist read-only.")
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("optimizer.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
