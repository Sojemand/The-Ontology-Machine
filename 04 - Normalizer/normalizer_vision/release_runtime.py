"""Helpers for release-backed Normalizer runtime state."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .runtime_semantic_assets import validate_release_payload
from .runtime_semantic_assets.policy import build_projection_catalog as build_runtime_projection_catalog
from .runtime_semantic_assets.semantic_policy import build_semantic_extraction_policy
from .taxonomy import TaxonomyProfile, build_profile_from_master


@dataclass(frozen=True, slots=True)
class ReleaseRuntime:
    profiles: dict[str, TaxonomyProfile]
    fallback_profile: TaxonomyProfile
    catalog_version: str


def build_release_runtime(
    release_payload: dict[str, Any],
    *,
    preferred_profile_id: str | None = None,
) -> ReleaseRuntime:
    release = validate_release_payload(release_payload)
    profiles = _build_profiles(release)
    fallback_projection_id = _resolve_fallback_projection_id(release, preferred_profile_id=preferred_profile_id)
    catalog = build_runtime_projection_catalog(release)
    return ReleaseRuntime(
        profiles=profiles,
        fallback_profile=profiles[fallback_projection_id],
        catalog_version=catalog.catalog_version,
    )


def _build_profiles(release: dict[str, Any]) -> dict[str, TaxonomyProfile]:
    master = deepcopy(dict(release["master_taxonomy"]))
    profiles: dict[str, TaxonomyProfile] = {}
    for raw_projection in release.get("projections", []) or []:
        if not isinstance(raw_projection, dict):
            continue
        projection_id = str(raw_projection.get("projection_id") or "").strip()
        if not projection_id:
            continue
        profiles[projection_id] = build_profile_from_master(master, deepcopy(raw_projection))
    if not profiles:
        raise ValueError("Semantic Release enthaelt keine nutzbaren Projection-Profile.")
    return profiles


def _resolve_fallback_projection_id(
    release: dict[str, Any],
    *,
    preferred_profile_id: str | None,
) -> str:
    requested = str(preferred_profile_id or "").strip() or None
    policy = build_semantic_extraction_policy(release, fallback_projection_id=requested)
    fallback_projection_id = str(policy.defaults.get("fallback_projection_id") or "").strip()
    if not fallback_projection_id:
        raise ValueError("Semantic Release enthaelt kein gueltiges Fallback-Profil.")
    return fallback_projection_id
