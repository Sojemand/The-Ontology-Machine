"""Validation entrypoints for edit-contract surfaces."""
from __future__ import annotations

from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    OCR_PROMPT_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)


def validate_surface(surface_id: str, value: dict) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        from ingestion_layer_file.models.validation import validate_config_payload

        return validate_config_payload(value)
    if surface_id == OCR_PROMPT_SURFACE_ID:
        from .prompt_repository import validate_ocr_prompt

        return validate_ocr_prompt(value)
    if surface_id == OUTPUT_CONTRACT_PREVIEW_SURFACE_ID:
        raise ValueError("optimizer.output_contract_preview ist read-only.")
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("optimizer.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
