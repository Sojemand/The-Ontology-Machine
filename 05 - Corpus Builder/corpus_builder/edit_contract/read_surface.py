"""Read operations for edit-contract surfaces."""

from __future__ import annotations

from . import config_repository, repository
from .types import (
    DEBUG_CAPABILITIES_SURFACE_ID,
    EMBEDDINGS_POLICY_SURFACE_ID,
    SEARCH_POLICY_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)


def read_surface(surface_id: str, *, module_root, preloaded_surfaces: dict[str, dict] | None = None) -> dict:
    if preloaded_surfaces is not None and surface_id in preloaded_surfaces:
        return preloaded_surfaces[surface_id]
    if surface_id == SETTINGS_SURFACE_ID:
        return config_repository.read_settings(module_root)
    if surface_id == EMBEDDINGS_POLICY_SURFACE_ID:
        return config_repository.read_embeddings(module_root)
    if surface_id == SEARCH_POLICY_SURFACE_ID:
        return repository.read_search_policy(module_root)
    if surface_id == DEBUG_CAPABILITIES_SURFACE_ID:
        return repository.read_debug_capabilities(module_root)
    raise ValueError(f"Unbekannte Surface: {surface_id}")
