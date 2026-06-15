"""Validation helpers for runtime-semantic bundle payloads."""

from __future__ import annotations

from typing import Any

from .runtime_semantic_assets_parsing import (
    require_canonical_runtime_locale,
    require_dict,
    require_list,
    require_matching_optional_text,
    require_matching_text,
    require_optional_text,
    require_text,
)


def validated_runtime_semantic_assets(payload: Any, *, release: dict[str, Any]) -> dict[str, Any]:
    assets = require_dict(payload, "runtime_semantic_assets")
    expected_release_id = require_text(release.get("release_id"), "release.release_id")
    expected_release_version = require_text(release.get("release_version"), "release.release_version")
    expected_release_fingerprint = require_text(release.get("fingerprint"), "release.fingerprint")
    expected_master_taxonomy_id = require_text(release.get("master_taxonomy_id"), "release.master_taxonomy_id")
    expected_master_taxonomy_version = require_text(release.get("master_taxonomy_version"), "release.master_taxonomy_version")
    expected_master_taxonomy_release_id = require_optional_text(
        release.get("master_taxonomy_release_id"),
        "release.master_taxonomy_release_id",
    )
    expected_runtime_locale = require_canonical_runtime_locale(
        require_optional_text(
            release.get("runtime_locale"),
            "release.runtime_locale",
        ),
        "release.runtime_locale",
    )
    release_fingerprint = require_matching_text(
        assets.get("release_fingerprint"),
        "runtime_semantic_assets.release_fingerprint",
        expected_release_fingerprint,
        "runtime_semantic_assets.release_fingerprint does not match the active semantic release.",
    )
    projection_catalog = require_dict(
        assets.get("projection_catalog"),
        "runtime_semantic_assets.projection_catalog",
    )
    bundle = require_dict(assets.get("vision_policy_bundle"), "runtime_semantic_assets.vision_policy_bundle")
    require_text(assets.get("schema_version"), "runtime_semantic_assets.schema_version")
    require_matching_text(
        assets.get("release_id"),
        "runtime_semantic_assets.release_id",
        expected_release_id,
        "runtime_semantic_assets.release_id does not match the active semantic release.",
    )
    require_matching_text(
        assets.get("release_version"),
        "runtime_semantic_assets.release_version",
        expected_release_version,
        "runtime_semantic_assets.release_version does not match the active semantic release.",
    )
    require_matching_text(
        assets.get("master_taxonomy_id"),
        "runtime_semantic_assets.master_taxonomy_id",
        expected_master_taxonomy_id,
        "runtime_semantic_assets.master_taxonomy_id does not match the active semantic release.",
    )
    require_matching_text(
        assets.get("master_taxonomy_version"),
        "runtime_semantic_assets.master_taxonomy_version",
        expected_master_taxonomy_version,
        "runtime_semantic_assets.master_taxonomy_version does not match the active semantic release.",
    )
    master_taxonomy_release_id = require_matching_optional_text(
        assets.get("master_taxonomy_release_id"),
        "runtime_semantic_assets.master_taxonomy_release_id",
        expected_master_taxonomy_release_id,
        "runtime_semantic_assets.master_taxonomy_release_id does not match the active semantic release.",
    )
    runtime_locale = require_canonical_runtime_locale(
        require_matching_optional_text(
            assets.get("runtime_locale"),
            "runtime_semantic_assets.runtime_locale",
            expected_runtime_locale,
            "runtime_semantic_assets.runtime_locale does not match the active semantic release.",
        ),
        "runtime_semantic_assets.runtime_locale",
    )
    require_text(projection_catalog.get("catalog_version"), "projection_catalog.catalog_version")
    require_matching_text(
        projection_catalog.get("release_id"),
        "projection_catalog.release_id",
        expected_release_id,
        "projection_catalog.release_id does not match the active semantic release.",
    )
    require_matching_text(
        projection_catalog.get("release_version"),
        "projection_catalog.release_version",
        expected_release_version,
        "projection_catalog.release_version does not match the active semantic release.",
    )
    require_matching_text(
        projection_catalog.get("release_fingerprint"),
        "projection_catalog.release_fingerprint",
        release_fingerprint,
        "projection_catalog.release_fingerprint does not match the runtime bundle.",
    )
    require_matching_text(
        projection_catalog.get("master_taxonomy_id"),
        "projection_catalog.master_taxonomy_id",
        expected_master_taxonomy_id,
        "projection_catalog.master_taxonomy_id does not match the active semantic release.",
    )
    require_matching_text(
        projection_catalog.get("master_taxonomy_version"),
        "projection_catalog.master_taxonomy_version",
        expected_master_taxonomy_version,
        "projection_catalog.master_taxonomy_version does not match the active semantic release.",
    )
    require_matching_optional_text(
        projection_catalog.get("master_taxonomy_release_id"),
        "projection_catalog.master_taxonomy_release_id",
        master_taxonomy_release_id,
        "projection_catalog.master_taxonomy_release_id does not match the runtime bundle.",
    )
    require_matching_optional_text(
        projection_catalog.get("master_taxonomy_release_id"),
        "projection_catalog.master_taxonomy_release_id",
        expected_master_taxonomy_release_id,
        "projection_catalog.master_taxonomy_release_id does not match the active semantic release.",
    )
    require_canonical_runtime_locale(
        require_matching_optional_text(
            projection_catalog.get("runtime_locale"),
            "projection_catalog.runtime_locale",
            runtime_locale,
            "projection_catalog.runtime_locale does not match the runtime bundle.",
        ),
        "projection_catalog.runtime_locale",
    )
    require_canonical_runtime_locale(
        require_matching_optional_text(
            projection_catalog.get("runtime_locale"),
            "projection_catalog.runtime_locale",
            expected_runtime_locale,
            "projection_catalog.runtime_locale does not match the active semantic release.",
        ),
        "projection_catalog.runtime_locale",
    )
    require_list(projection_catalog.get("projections"), "projection_catalog.projections")
    require_text(bundle.get("bundle_version"), "vision_policy_bundle.bundle_version")
    require_matching_text(
        bundle.get("release_fingerprint"),
        "vision_policy_bundle.release_fingerprint",
        release_fingerprint,
        "vision_policy_bundle.release_fingerprint does not match the runtime bundle.",
    )
    require_dict(bundle.get("ocr_policy"), "vision_policy_bundle.ocr_policy")
    return assets
