from __future__ import annotations

from pathlib import Path
from typing import Any


def _release_detail(corpus_db_path: Path) -> dict[str, object]:
    release = _release_payload()
    runtime_assets = _runtime_assets(release)
    return {
        "status": {"active_release_id": release["release_id"]},
        "release": release,
        "release_id": release["release_id"],
        "release_version": release["release_version"],
        "fingerprint": release["fingerprint"],
        "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
        "master_taxonomy_release_id": release["master_taxonomy_release_id"],
        "runtime_locale": release["runtime_locale"],
        "active_snapshot": {
            "snapshot_id": "sha256:test-snapshot",
            "release": {**release, "active_snapshot": {"snapshot_id": "sha256:test-snapshot", "release_path": str(corpus_db_path.parent / "semantic_release.active.json")}},
            "projection_catalog": dict(runtime_assets["projection_catalog"]),
            "runtime_semantic_assets": runtime_assets,
            "master_taxonomy_release_id": release["master_taxonomy_release_id"],
            "runtime_locale": release["runtime_locale"],
            "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
        },
    }


def _release_payload() -> dict[str, object]:
    return {
        "release_id": "semantic_release.default",
        "release_version": "1",
        "master_taxonomy_id": "taxonomy.default",
        "master_taxonomy_version": "2026-04-02.v1",
        "master_taxonomy_release_id": "sha256:master-line",
        "runtime_locale": "en",
        "projection_ids": ["finance.default.v1"],
        "materialization_version": "materialization.v1",
        "fingerprint": "sha256:semantic-default",
        "master_taxonomy": {"taxonomy_id": "taxonomy.default"},
        "projections": [
            {
                "projection_id": "finance.default.v1",
                "label": "Finance",
                "routing": {
                    "when_to_use": "Invoices and payment documents.",
                    "avoid_when": "Legal or public administration documents.",
                    "example_document_types": ["invoice"],
                },
            }
        ],
    }


def _runtime_assets(release: dict[str, object]) -> dict[str, object]:
    fingerprint = str(release["fingerprint"])
    return {
        "schema_version": "runtime_semantic_assets_v1",
        "release_id": str(release["release_id"]),
        "release_version": str(release["release_version"]),
        "release_fingerprint": fingerprint,
        "master_taxonomy_id": str(release["master_taxonomy_id"]),
        "master_taxonomy_version": str(release["master_taxonomy_version"]),
        "master_taxonomy_release_id": str(release["master_taxonomy_release_id"]),
        "runtime_locale": str(release["runtime_locale"]),
        "projection_catalog": {
            "catalog_version": "sha256:runtime-test",
            "release_id": str(release["release_id"]),
            "release_version": str(release["release_version"]),
            "release_fingerprint": fingerprint,
            "master_taxonomy_id": str(release["master_taxonomy_id"]),
            "master_taxonomy_version": str(release["master_taxonomy_version"]),
            "master_taxonomy_release_id": str(release["master_taxonomy_release_id"]),
            "runtime_locale": str(release["runtime_locale"]),
            "projections": [],
        },
        "vision_policy_bundle": {
            "bundle_version": "vision_policy_bundle_v1",
            "release_fingerprint": fingerprint,
            "ocr_policy": {
                "policy_version": "ocr_policy_v1",
                "source_mode": "legacy_defaults",
                "defaults": {},
                "projection_overrides": {},
            },
            "semantic_extraction_policy": {
                "policy_version": "semantic_extraction_policy_v1",
                "source_mode": "legacy_defaults",
                "defaults": {},
                "projection_overrides": {},
            },
        },
    }


def _set_path(payload: dict[str, object], path: tuple[str, ...], value: Any) -> None:
    cursor: dict[str, Any] = payload
    for segment in path[:-1]:
        cursor = cursor[segment]
    cursor[path[-1]] = value
