"""Read operations for edit-contract surfaces."""
from __future__ import annotations

from . import repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    OCR_PROMPT_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)


def read_surface(surface_id: str, *, layout, module_root) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        from . import settings_repository

        return settings_repository.read_settings(layout)
    if surface_id == OCR_PROMPT_SURFACE_ID:
        from . import prompt_repository

        return prompt_repository.read_ocr_prompt(layout)
    if surface_id == OUTPUT_CONTRACT_PREVIEW_SURFACE_ID:
        return repository.read_output_contract_preview(module_root)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        return repository.read_debug_capabilities(module_root)
    raise ValueError(f"Unbekannte Surface: {surface_id}")
