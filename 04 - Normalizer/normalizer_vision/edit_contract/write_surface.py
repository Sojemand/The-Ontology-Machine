"""Write operations for Normalizer edit-contract surfaces."""
from __future__ import annotations

from ..source_authoring import glossary_surface, master_surface, profiles_surface, release_surface
from . import repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    PROMPT_OVERRIDES_SURFACE_ID,
    SEMANTIC_RELEASE_AUTHORING_SURFACE_ID,
    SETTINGS_SURFACE_ID,
    TAXONOMY_MASTER_SURFACE_ID,
    TAXONOMY_PROFILES_SURFACE_ID,
    TAXONOMY_RELEASE_DRAFT_SURFACE_ID,
    TRANSLATION_GLOSSARY_SURFACE_ID,
)


def write_surface(surface_id: str, value: dict, *, module_root) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        return repository.write_settings(module_root, value)
    if surface_id == PROMPT_OVERRIDES_SURFACE_ID:
        return repository.write_prompt_overrides(module_root, value)
    if surface_id == PROMPT_BUNDLE_SURFACE_ID:
        return repository.write_prompt_bundle(module_root, value)
    if surface_id == TAXONOMY_MASTER_SURFACE_ID:
        return master_surface.write_surface(module_root, value)
    if surface_id == TAXONOMY_PROFILES_SURFACE_ID:
        return profiles_surface.write_surface(module_root, value)
    if surface_id == TRANSLATION_GLOSSARY_SURFACE_ID:
        return glossary_surface.write_surface(module_root, value)
    if surface_id == SEMANTIC_RELEASE_AUTHORING_SURFACE_ID:
        return release_surface.write_surface(module_root, value)
    if surface_id == TAXONOMY_RELEASE_DRAFT_SURFACE_ID:
        return repository.write_taxonomy_release_draft(module_root, value)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("normalizer.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
