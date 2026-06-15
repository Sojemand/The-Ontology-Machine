from __future__ import annotations

import sqlite3
from typing import Any

from .inspection_rows import (
    affected_documents,
    classification_coverage,
    issue_clusters,
    projection_coverage,
    promotion_coverage,
    slot_coverage,
)


def fetch_analysis_snapshot(
    conn: sqlite3.Connection,
    *,
    release_fingerprint: str,
) -> dict[str, Any]:
    document_count = _count(conn, "SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0")
    archived_count = _count(conn, "SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 1")
    payload_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN structured_json IS NOT NULL AND structured_json != '' THEN 1 ELSE 0 END) AS structured_payloads,
            SUM(CASE WHEN normalized_json IS NOT NULL AND normalized_json != '' THEN 1 ELSE 0 END) AS normalized_payloads,
            SUM(CASE WHEN projection_json IS NOT NULL AND projection_json != '' THEN 1 ELSE 0 END) AS projection_payloads,
            COUNT(DISTINCT NULLIF(release_fingerprint, '')) AS release_fingerprint_count
        FROM document_payloads
        """
    ).fetchone()
    state_row = conn.execute(
        """
        SELECT
            COUNT(*) AS materialized_documents,
            SUM(CASE WHEN COALESCE(materialization_state, 'legacy') = 'current' THEN 1 ELSE 0 END) AS current_materializations,
            COUNT(DISTINCT NULLIF(projection_id, '')) AS projection_count
        FROM document_processing_state
        """
    ).fetchone()
    entity_row = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM evidence_atoms) AS evidence_atoms,
            (SELECT COUNT(*) FROM slot_candidates) AS slot_candidates,
            (SELECT COUNT(*) FROM document_promotions WHERE COALESCE(is_current, 1) = 1) AS document_promotions,
            (SELECT COUNT(DISTINCT document_id) FROM document_promotions WHERE COALESCE(is_current, 1) = 1) AS documents_with_promotions,
            (SELECT COUNT(DISTINCT slot) FROM document_promotions WHERE COALESCE(is_current, 1) = 1) AS promotion_slot_count,
            (SELECT COUNT(*) FROM document_entities) AS entities,
            (SELECT COUNT(*) FROM entity_relations) AS relations,
            (SELECT COUNT(*) FROM materialization_audit) AS materialization_audits
        """
    ).fetchone()
    review_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN COALESCE(needs_review, 0) = 1 THEN 1 ELSE 0 END) AS needs_review,
            SUM(CASE WHEN COALESCE(interpreter_needs_review, 0) = 1 THEN 1 ELSE 0 END) AS interpreter_review,
            SUM(CASE WHEN COALESCE(normalizer_needs_review, 0) = 1 THEN 1 ELSE 0 END) AS normalizer_review,
            SUM(CASE WHEN COALESCE(validator_issues_count, 0) > 0 THEN 1 ELSE 0 END) AS validator_issues
        FROM documents
        WHERE COALESCE(is_archived, 0) = 0
        """
    ).fetchone()
    return {
        "document_count": document_count,
        "archived_count": archived_count,
        "structured_payloads": int(payload_row["structured_payloads"] or 0),
        "normalized_payloads": int(payload_row["normalized_payloads"] or 0),
        "projection_payloads": int(payload_row["projection_payloads"] or 0),
        "release_fingerprint_count": int(payload_row["release_fingerprint_count"] or 0),
        "materialized_documents": int(state_row["materialized_documents"] or 0),
        "current_materializations": int(state_row["current_materializations"] or 0),
        "projection_count": int(state_row["projection_count"] or 0),
        "evidence_atoms": int(entity_row["evidence_atoms"] or 0),
        "slot_candidates": int(entity_row["slot_candidates"] or 0),
        "document_promotions": int(entity_row["document_promotions"] or 0),
        "documents_with_promotions": int(entity_row["documents_with_promotions"] or 0),
        "promotion_slot_count": int(entity_row["promotion_slot_count"] or 0),
        "entities": int(entity_row["entities"] or 0),
        "relations": int(entity_row["relations"] or 0),
        "materialization_audits": int(entity_row["materialization_audits"] or 0),
        "needs_review_count": int(review_row["needs_review"] or 0),
        "interpreter_review_count": int(review_row["interpreter_review"] or 0),
        "normalizer_review_count": int(review_row["normalizer_review"] or 0),
        "validator_issue_count": int(review_row["validator_issues"] or 0),
        "classification_coverage": classification_coverage(conn),
        "projection_coverage": projection_coverage(conn),
        "slot_coverage": slot_coverage(conn),
        "promotion_coverage": promotion_coverage(conn),
        "affected_documents": affected_documents(conn),
        "issue_clusters": issue_clusters(review_row, entity_row),
        "active_release_fingerprint": _active_release_fingerprint(conn),
        "release_match_count": _count(
            conn,
            "SELECT COUNT(*) FROM document_payloads WHERE release_fingerprint = ?",
            (release_fingerprint,),
        )
        if release_fingerprint
        else 0,
    }


def _active_release_fingerprint(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT active_release_fingerprint FROM installation_state WHERE singleton = 1"
    ).fetchone()
    return str(row["active_release_fingerprint"] or "") if row else ""


def _count(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return 0
    return int(row[0] or 0)
