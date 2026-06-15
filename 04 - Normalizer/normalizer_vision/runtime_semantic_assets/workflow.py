"""Workflow orchestration for runtime semantic asset compilation."""
from __future__ import annotations

from . import policy, validation
from .types import RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION, RuntimeSemanticAssets


def build_runtime_semantic_assets(release_payload: dict[str, object]) -> RuntimeSemanticAssets:
    release = validation.validate_release_payload(release_payload)
    projection_catalog = policy.build_projection_catalog(release)
    vision_policy_bundle = policy.build_vision_policy_bundle(release, release_fingerprint=str(release.get("fingerprint") or ""))
    assets = RuntimeSemanticAssets(
        schema_version=RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION,
        release_id=str(release.get("release_id") or ""),
        release_version=str(release.get("release_version") or ""),
        release_fingerprint=str(release.get("fingerprint") or ""),
        master_taxonomy_id=str(release.get("master_taxonomy_id") or ""),
        master_taxonomy_version=str(release.get("master_taxonomy_version") or ""),
        promotion_slots=_promotion_slots(release),
        master_taxonomy_release_id=str(release.get("master_taxonomy_release_id") or "").strip() or None,
        runtime_locale=str(release.get("runtime_locale") or "").strip() or None,
        projection_catalog=projection_catalog,
        vision_policy_bundle=vision_policy_bundle,
    )
    validation.validate_runtime_semantic_assets(assets.to_dict())
    return assets


def _promotion_slots(release: dict[str, object]) -> list[dict[str, object]]:
    master = release.get("master_taxonomy")
    if not isinstance(master, dict):
        return []
    slots = master.get("promotion_slots")
    if not isinstance(slots, list):
        return []
    return [dict(item) for item in slots if isinstance(item, dict) and item.get("slot")]
