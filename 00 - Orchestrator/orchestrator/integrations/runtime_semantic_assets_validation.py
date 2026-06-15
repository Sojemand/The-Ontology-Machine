"""Validation helpers for runtime-semantic release and bundle payloads."""

from __future__ import annotations

from typing import Any

from .runtime_semantic_assets_bundle_validation import validated_runtime_semantic_assets
from .runtime_semantic_assets_parsing import (
    require_canonical_runtime_locale,
    require_dict,
    require_matching_text,
    require_optional_text,
    require_text,
)


def validated_release_detail(payload: Any) -> dict[str, Any]:
    detail = require_dict(payload, "release_detail")
    release = require_dict(detail.get("release"), "release_detail.release")
    release_id = require_text(detail.get("release_id") or release.get("release_id"), "release_detail.release_id")
    release_version = require_text(
        detail.get("release_version") or release.get("release_version"),
        "release_detail.release_version",
    )
    fingerprint = require_text(detail.get("fingerprint") or release.get("fingerprint"), "release_detail.fingerprint")
    require_text(detail.get("release_path"), "release_detail.release_path")
    require_dict(detail.get("status"), "release_detail.status")
    master_taxonomy_release_id = require_optional_text(
        detail.get("master_taxonomy_release_id") or release.get("master_taxonomy_release_id"),
        "release_detail.master_taxonomy_release_id",
    )
    runtime_locale = require_canonical_runtime_locale(
        require_optional_text(
            detail.get("runtime_locale") or release.get("runtime_locale"),
            "release_detail.runtime_locale",
        ),
        "release_detail.runtime_locale",
    )
    active_snapshot = detail.get("active_snapshot")
    if active_snapshot is not None:
        detail["active_snapshot"] = validated_active_snapshot(active_snapshot, release=release)
    detail["release"] = release
    detail["release_id"] = release_id
    detail["release_version"] = release_version
    detail["fingerprint"] = fingerprint
    if master_taxonomy_release_id:
        detail["master_taxonomy_release_id"] = master_taxonomy_release_id
    if runtime_locale:
        detail["runtime_locale"] = runtime_locale
    return detail


def validated_active_snapshot(payload: Any, *, release: dict[str, Any]) -> dict[str, Any]:
    snapshot = require_dict(payload, "release_detail.active_snapshot")
    snapshot_id = require_text(snapshot.get("snapshot_id"), "release_detail.active_snapshot.snapshot_id")
    snapshot_release = require_dict(snapshot.get("release"), "release_detail.active_snapshot.release")
    require_matching_text(
        snapshot_release.get("release_id"),
        "release_detail.active_snapshot.release.release_id",
        require_text(release.get("release_id"), "release.release_id"),
        "active_snapshot.release.release_id does not match the release detail.",
    )
    require_matching_text(
        snapshot_release.get("release_version"),
        "release_detail.active_snapshot.release.release_version",
        require_text(release.get("release_version"), "release.release_version"),
        "active_snapshot.release.release_version does not match the release detail.",
    )
    require_matching_text(
        snapshot_release.get("fingerprint"),
        "release_detail.active_snapshot.release.fingerprint",
        require_text(release.get("fingerprint"), "release.fingerprint"),
        "active_snapshot.release.fingerprint does not match the release detail.",
    )
    projection_catalog = require_dict(
        snapshot.get("projection_catalog"),
        "release_detail.active_snapshot.projection_catalog",
    )
    runtime_assets = validated_runtime_semantic_assets(
        require_dict(
            snapshot.get("runtime_semantic_assets"),
            "release_detail.active_snapshot.runtime_semantic_assets",
        ),
        release=snapshot_release,
    )
    require_matching_text(
        projection_catalog.get("release_fingerprint"),
        "release_detail.active_snapshot.projection_catalog.release_fingerprint",
        require_text(snapshot_release.get("fingerprint"), "release_detail.active_snapshot.release.fingerprint"),
        "active_snapshot.projection_catalog.release_fingerprint does not match the snapshot release.",
    )
    snapshot["snapshot_id"] = snapshot_id
    snapshot["release"] = snapshot_release
    snapshot["projection_catalog"] = projection_catalog
    snapshot["runtime_semantic_assets"] = runtime_assets
    snapshot["master_taxonomy_release_id"] = require_optional_text(
        snapshot.get("master_taxonomy_release_id") or snapshot_release.get("master_taxonomy_release_id"),
        "release_detail.active_snapshot.master_taxonomy_release_id",
    )
    snapshot["runtime_locale"] = require_canonical_runtime_locale(
        require_optional_text(
            snapshot.get("runtime_locale") or snapshot_release.get("runtime_locale"),
            "release_detail.active_snapshot.runtime_locale",
        ),
        "release_detail.active_snapshot.runtime_locale",
    )
    snapshot["release_path"] = require_text(
        snapshot.get("release_path"),
        "release_detail.active_snapshot.release_path",
    )
    return snapshot
