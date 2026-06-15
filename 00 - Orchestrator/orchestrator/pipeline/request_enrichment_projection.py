"""Projection-catalog validation helpers for request enrichment."""

from __future__ import annotations

import copy
from typing import Any

_OPTIONAL_CATALOG_METADATA_FIELDS = (
    "release_id",
    "release_version",
    "release_fingerprint",
    "master_taxonomy_id",
    "master_taxonomy_release_id",
    "runtime_locale",
)


def required_projection_catalog(projection_catalog: dict[str, Any] | None) -> dict[str, Any]:
    if projection_catalog is None:
        raise ValueError("projection_catalog is missing in the Runtime Semantics context.")
    return copy.deepcopy(validated_projection_catalog(projection_catalog))


def validated_projection_catalog(catalog: Any) -> dict[str, Any]:
    if not isinstance(catalog, dict):
        raise ValueError("projection_catalog is invalid.")
    if not str(catalog.get("catalog_version", "")).strip():
        raise ValueError("projection_catalog.catalog_version is missing.")
    if not str(catalog.get("master_taxonomy_version", "")).strip():
        raise ValueError("projection_catalog.master_taxonomy_version is missing.")
    if not isinstance(catalog.get("projections"), list):
        raise ValueError("projection_catalog.projections is missing.")
    normalized = {
        "catalog_version": str(catalog.get("catalog_version", "")).strip(),
        "master_taxonomy_version": str(catalog.get("master_taxonomy_version", "")).strip(),
        "projections": copy.deepcopy(catalog.get("projections", [])),
    }
    for field in _OPTIONAL_CATALOG_METADATA_FIELDS:
        if field in catalog and not str(catalog.get(field, "")).strip():
            raise ValueError(f"projection_catalog.{field} is missing.")
        if field in catalog:
            value = str(catalog.get(field, "")).strip()
            if field == "runtime_locale" and value != "en":
                raise ValueError("projection_catalog.runtime_locale must be en.")
            normalized[field] = value
    return normalized
