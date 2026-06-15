from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import path_hash


def required_database_path(payload: Mapping[str, Any]) -> str:
    database_ref = mapping(payload, "database_ref")
    database_path = str(payload.get("database_path") or database_ref.get("database_path") or "").strip()
    if not database_path:
        raise ValueError("database_path is required.")
    return database_path


def resolve_artifact_root(payload: Mapping[str, Any], db_path: Path) -> Path:
    candidate = str(payload.get("artifact_root") or "").strip()
    if candidate:
        return Path(candidate).resolve(strict=False)
    if db_path.parent.name.lower() == "corpus":
        return db_path.parent.parent.resolve(strict=False)
    return db_path.parent.resolve(strict=False)


def validated_materialization_refs(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = payload.get("release_materialization_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("materialization_refs_missing: release_materialization_refs is required.")
    return [dict(item) for item in refs if isinstance(item, Mapping)]


def validate_target_identity(
    payload: Mapping[str, Any],
    db_path: Path,
    artifact_root: Path,
    active_release: Mapping[str, Any],
) -> None:
    target_identity = mapping(payload, "target_identity")
    claimed_db_hash = str(target_identity.get("database_path_hash") or payload.get("database_path_hash") or "").strip()
    if not claimed_db_hash:
        raise ValueError("target_identity_unproven: database_path_hash is required.")
    if claimed_db_hash != path_hash(db_path):
        raise ValueError("target_identity_unproven: database_path_hash mismatch.")
    claimed_artifact_hash = str(target_identity.get("artifact_root_path_hash") or "").strip()
    if claimed_artifact_hash and claimed_artifact_hash != path_hash(artifact_root):
        raise ValueError("target_identity_unproven: artifact_root_path_hash mismatch.")
    claimed_release_fingerprint = str(target_identity.get("release_fingerprint") or "").strip()
    release_fingerprint = str(active_release.get("release_fingerprint") or "").strip()
    if claimed_release_fingerprint and release_fingerprint and claimed_release_fingerprint != release_fingerprint:
        raise ValueError("target_identity_unproven: release_fingerprint mismatch.")


def query_manifest(payload: Mapping[str, Any], database_ref: Mapping[str, Any]) -> dict[str, Any]:
    supplied = payload.get("query_manifest")
    if isinstance(supplied, Mapping):
        return dict(supplied)
    return {
        "schema_version": "kernel.database_query_manifest.v1",
        "database_ref": dict(database_ref),
        "queries": [
            {"name": "document_counts", "sql": "SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0"},
            {"name": "classification_coverage", "sql": "SELECT category, document_type, COUNT(*) FROM documents GROUP BY category, document_type"},
            {"name": "projection_coverage", "sql": "SELECT projection_id, projection_fingerprint, COUNT(*) FROM document_processing_state GROUP BY projection_id, projection_fingerprint"},
            {"name": "promotion_coverage", "sql": "SELECT slot, COUNT(DISTINCT document_id), COUNT(*) FROM document_promotions WHERE COALESCE(is_current, 1) = 1 GROUP BY slot"},
        ],
    }


def materialized_batches(
    materialization_refs: list[dict[str, Any]],
    release_fingerprint: str,
    release_match_count: int,
) -> list[dict[str, Any]]:
    explicit_batches = [
        dict(item)
        for item in materialization_refs
        if isinstance(item.get("pipeline_batch_id"), str) and item.get("pipeline_batch_id")
    ]
    if explicit_batches:
        return explicit_batches
    return [
        {
            "pipeline_batch_id": "pbt_inferred_materialization",
            "release_fingerprint": release_fingerprint,
            "record_count": release_match_count,
        }
    ]


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}
