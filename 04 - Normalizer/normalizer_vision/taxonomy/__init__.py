"""Path-stable surface for taxonomy loading, validation, and projection helpers."""
from __future__ import annotations

from .policy import upgrade_master_taxonomy_v2, upgrade_projection_payload_v2
from .surface_signals import default_surface_signals, projection_surface_signals
from .types import (
    DEFAULT_MATERIALIZATION_PROFILE_ID,
    DEFAULT_PROJECTION_FAMILY,
    DEFAULT_PROJECTION_VERSION,
    MASTER_REQUIRED_KEYS,
    PROJECTION_REQUIRED_KEYS,
    PROJECTION_SECTION_SPECS,
    SEMANTIC_RELEASE_SCHEMA_VERSION,
    TaxonomyProfile,
    profile_to_json,
)
from .workflow import (
    build_profile_from_master,
    build_profiles_from_compiled_master,
    build_projection_payload,
    find_projection_template,
    projection_payload_from_domains,
    projection_payload_from_template,
    validate_master_taxonomy,
)

__all__ = [
    "DEFAULT_MATERIALIZATION_PROFILE_ID",
    "DEFAULT_PROJECTION_FAMILY",
    "DEFAULT_PROJECTION_VERSION",
    "MASTER_REQUIRED_KEYS",
    "PROJECTION_REQUIRED_KEYS",
    "PROJECTION_SECTION_SPECS",
    "SEMANTIC_RELEASE_SCHEMA_VERSION",
    "TaxonomyProfile",
    "build_profile_from_master",
    "build_profiles_from_compiled_master",
    "build_projection_payload",
    "default_surface_signals",
    "find_projection_template",
    "profile_to_json",
    "projection_payload_from_domains",
    "projection_payload_from_template",
    "projection_surface_signals",
    "upgrade_master_taxonomy_v2",
    "upgrade_projection_payload_v2",
    "validate_master_taxonomy",
]
