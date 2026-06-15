"""Local import shim for module-local semantic identity helpers."""
from __future__ import annotations

from vision_pipeline_shared.semantic_identity import (  # noqa: E402
    build_master_taxonomy_release_id,
    build_projection_catalog_version,
    build_release_fingerprint,
    canonical_locale_list,
    canonical_projection_id_list,
    legacy_master_taxonomy_release_id,
    normalize_projection_catalog_payload,
    normalize_release_fingerprint_payload,
    resolve_master_taxonomy_release_id,
)

__all__ = [
    "build_master_taxonomy_release_id",
    "build_projection_catalog_version",
    "build_release_fingerprint",
    "canonical_locale_list",
    "canonical_projection_id_list",
    "legacy_master_taxonomy_release_id",
    "normalize_projection_catalog_payload",
    "normalize_release_fingerprint_payload",
    "resolve_master_taxonomy_release_id",
]
