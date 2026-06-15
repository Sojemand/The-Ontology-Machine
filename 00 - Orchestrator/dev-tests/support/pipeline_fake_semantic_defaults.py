from __future__ import annotations

from pathlib import Path


def default_release() -> dict[str, object]:
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


def default_runtime_semantic_assets(release: dict[str, object]) -> dict[str, object]:
    fingerprint = str(release.get("fingerprint") or "")
    projection_catalog = {
        "catalog_version": "sha256:runtime-test",
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "release_fingerprint": fingerprint,
        "master_taxonomy_id": str(release.get("master_taxonomy_id") or ""),
        "master_taxonomy_version": str(release.get("master_taxonomy_version") or ""),
        "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
        "runtime_locale": str(release.get("runtime_locale") or ""),
        "projections": [
            {
                "projection_id": "finance.default.v1",
                "label": "Finance",
                "when_to_use": "Invoices and payment documents.",
                "avoid_when": "Legal or public administration documents.",
                "example_document_types": ["invoice"],
            }
        ],
    }
    return {
        "schema_version": "runtime_semantic_assets_v1",
        "release_id": str(release.get("release_id") or ""),
        "release_version": str(release.get("release_version") or ""),
        "release_fingerprint": fingerprint,
        "master_taxonomy_id": str(release.get("master_taxonomy_id") or ""),
        "master_taxonomy_version": str(release.get("master_taxonomy_version") or ""),
        "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
        "runtime_locale": str(release.get("runtime_locale") or ""),
        "projection_catalog": projection_catalog,
        "vision_policy_bundle": {
            "bundle_version": "vision_policy_bundle_v1",
            "release_fingerprint": fingerprint,
            "ocr_policy": {"policy_version": "ocr_policy_v1", "source_mode": "legacy_defaults", "defaults": {}, "projection_overrides": {}},
            "semantic_extraction_policy": {
                "policy_version": "semantic_extraction_policy_v1",
                "source_mode": "legacy_defaults",
                "defaults": {},
                "projection_overrides": {},
            },
        },
    }


def default_active_snapshot(corpus_db_path: Path, release: dict[str, object]) -> dict[str, object]:
    runtime_assets = default_runtime_semantic_assets(release)
    return {
        "snapshot_id": "sha256:test-snapshot",
        "release": {
            **release,
            "active_snapshot": {
                "snapshot_id": "sha256:test-snapshot",
                "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
            },
        },
        "projection_catalog": dict(runtime_assets["projection_catalog"]),
        "runtime_semantic_assets": runtime_assets,
        "master_taxonomy_release_id": str(release["master_taxonomy_release_id"]),
        "runtime_locale": str(release["runtime_locale"]),
        "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
    }


def default_activation_preflight(corpus_db_path: Path, release_path: Path) -> dict[str, object]:
    release = default_release()
    return {
        "current_snapshot": {"snapshot_id": "sha256:test-snapshot", "release": dict(release)},
        "next_snapshot": {"snapshot_id": "sha256:test-snapshot", "release": {**release, "release_path": str(release_path)}},
        "runtime_locale": {
            "current": {"value": str(release["runtime_locale"]), "provenance": "release"},
            "next": {"value": str(release["runtime_locale"]), "provenance": "release"},
        },
        "db_changes": {
            "active_snapshot_id_before": "sha256:test-snapshot",
            "active_snapshot_id_after": "sha256:test-snapshot",
            "projection_drift_documents": 0,
            "stale_documents_after_activation": 0,
        },
        "allowed_actions": ["cancel"],
        "requires_confirmation": False,
        "initialization_required": False,
        "confirmation_artifact_template": {
            "artifact_version": "semantic_activation_confirmation_v1",
            "corpus_db_path": str(corpus_db_path),
            "release_path": str(release_path),
            "expected_current_snapshot_id": "sha256:test-snapshot",
            "expected_new_snapshot_id": "sha256:test-snapshot",
            "expected_release_fingerprint": str(release["fingerprint"]),
            "expected_master_taxonomy_release_id": str(release["master_taxonomy_release_id"]),
            "expected_runtime_locale": str(release["runtime_locale"]),
            "decision": "activate_only",
        },
        "no_op": True,
    }
