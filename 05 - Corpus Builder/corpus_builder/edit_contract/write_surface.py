"""Write operations for edit-contract surfaces."""

from __future__ import annotations

from . import config_repository, repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EMBEDDINGS_POLICY_SURFACE_ID,
    SEARCH_POLICY_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)


def write_surface(surface_id: str, value: dict, *, module_root) -> dict:
    if surface_id == SETTINGS_SURFACE_ID:
        return config_repository.write_settings(module_root, value)
    if surface_id == EMBEDDINGS_POLICY_SURFACE_ID:
        return config_repository.write_embeddings(module_root, value)
    if surface_id == SEARCH_POLICY_SURFACE_ID:
        return repository.write_search_policy(module_root, value)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        raise ValueError("corpus_builder.debug_capabilities ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
