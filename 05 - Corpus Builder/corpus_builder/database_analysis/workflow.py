from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..database.repository_connection import connect
from ..semantic_release.multi_source_merge_types import owner_ok, path_hash
from .inspection import fetch_analysis_snapshot
from .workflow_support import (
    mapping,
    materialized_batches,
    query_manifest,
    ratio,
    required_database_path,
    resolve_artifact_root,
    validate_target_identity,
    validated_materialization_refs,
)


def read_database_analysis_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    database_path = required_database_path(payload)
    db_path = Path(database_path).resolve(strict=False)
    if not db_path.is_file():
        raise ValueError(f"database_missing: {db_path}")
    artifact_root = resolve_artifact_root(payload, db_path)
    active_release = mapping(payload, "active_release_ref") or mapping(payload, "semantic_release_ref")
    materialization_refs = validated_materialization_refs(payload)
    validate_target_identity(payload, db_path, artifact_root, active_release)

    with connect(str(db_path)) as conn:
        snapshot = fetch_analysis_snapshot(
            conn,
            release_fingerprint=str(active_release.get("release_fingerprint") or ""),
        )

    if snapshot["document_count"] <= 0:
        raise ValueError("database_empty: filled evidence requires at least one document.")

    requested_release_fingerprint = str(active_release.get("release_fingerprint") or "")
    actual_release_fingerprint = str(snapshot["active_release_fingerprint"] or "")
    if requested_release_fingerprint and actual_release_fingerprint and requested_release_fingerprint != actual_release_fingerprint:
        raise ValueError("release_fingerprint_mismatch: active installation state does not match the targeted release.")

    evidence = {
        "database_ref": {
            **mapping(payload, "database_ref"),
            "database_path": str(db_path),
            "database_path_hash": path_hash(db_path),
        },
        "semantic_release": dict(active_release),
        "semantic_release_ref": dict(active_release),
        "release_materialization": {
            "active_release": dict(active_release),
            "materialized_batches": materialized_batches(materialization_refs, requested_release_fingerprint, snapshot["release_match_count"]),
            "materialization_refs": materialization_refs,
            "mixed_release_versions": snapshot["release_fingerprint_count"] > 1,
            "current_release_record_count": snapshot["release_match_count"] or snapshot["document_count"],
        },
        "release_materialization_refs": materialization_refs,
        "database_summary": {
            "row_count": snapshot["document_count"],
            "archived_row_count": snapshot["archived_count"],
            "artifact_root_path": str(artifact_root),
            "document_count": snapshot["document_count"],
        },
        "coverage_metrics": {
            "documents_total": snapshot["document_count"],
            "structured_payload_coverage": ratio(snapshot["structured_payloads"], snapshot["document_count"]),
            "normalized_payload_coverage": ratio(snapshot["normalized_payloads"], snapshot["document_count"]),
            "projection_payload_coverage": ratio(snapshot["projection_payloads"], snapshot["document_count"]),
            "materialized_document_coverage": ratio(snapshot["materialized_documents"], snapshot["document_count"]),
            "review_flag_count": snapshot["needs_review_count"] + snapshot["interpreter_review_count"] + snapshot["normalizer_review_count"],
            "overall": ratio(snapshot["normalized_payloads"] + snapshot["materialized_documents"], snapshot["document_count"] * 2),
        },
        "classification_coverage": snapshot["classification_coverage"],
        "projection_coverage": snapshot["projection_coverage"],
        "raw_to_normalized_deltas": [],
        "field_coverage": {
            "structured_payloads": {
                "present_count": snapshot["structured_payloads"],
                "coverage_ratio": ratio(snapshot["structured_payloads"], snapshot["document_count"]),
            },
            "normalized_payloads": {
                "present_count": snapshot["normalized_payloads"],
                "coverage_ratio": ratio(snapshot["normalized_payloads"], snapshot["document_count"]),
            },
            "projection_payloads": {
                "present_count": snapshot["projection_payloads"],
                "coverage_ratio": ratio(snapshot["projection_payloads"], snapshot["document_count"]),
            },
            "document_promotions": {
                "present_count": snapshot["documents_with_promotions"],
                "coverage_ratio": ratio(snapshot["documents_with_promotions"], snapshot["document_count"]),
                "value_count": snapshot["document_promotions"],
                "slot_count": snapshot["promotion_slot_count"],
            },
        },
        "row_cell_coverage": {
            "evidence_atom_count": snapshot["evidence_atoms"],
            "slot_candidate_count": snapshot["slot_candidates"],
            "document_promotion_count": snapshot["document_promotions"],
        },
        "slot_coverage": snapshot["slot_coverage"],
        "promotion_coverage": snapshot["promotion_coverage"],
        "entity_coverage": {
            "entity_count": snapshot["entities"],
            "relation_count": snapshot["relations"],
            "materialization_audit_count": snapshot["materialization_audits"],
            "current_materializations": snapshot["current_materializations"],
            "projection_count": snapshot["projection_count"],
        },
        "issue_clusters": snapshot["issue_clusters"],
        "affected_documents": snapshot["affected_documents"],
    }
    manifest = query_manifest(payload, evidence["database_ref"])
    if manifest:
        evidence["query_manifest"] = manifest
    target_identity = mapping(payload, "target_identity")
    return owner_ok(
        owner_action="read_database_analysis_evidence",
        capability="database_analysis_evidence_reader",
        target_identity=target_identity,
        output_refs=evidence,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "read_database_analysis_evidence",
            "database_path_hash": evidence["database_ref"]["database_path_hash"],
            "release_fingerprint": requested_release_fingerprint,
        },
    )
