from __future__ import annotations

import sqlite3


def classification_coverage(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "category": str(row["category"] or ""),
            "document_type": str(row["document_type"] or ""),
            "count": int(row["row_count"] or 0),
        }
        for row in conn.execute(
            """
            SELECT category, document_type, COUNT(*) AS row_count
            FROM documents
            WHERE COALESCE(is_archived, 0) = 0
            GROUP BY category, document_type
            ORDER BY row_count DESC, category, document_type
            """
        ).fetchall()
    ]


def projection_coverage(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "projection_id": str(row["projection_id"] or ""),
            "projection_fingerprint": str(row["projection_fingerprint"] or ""),
            "count": int(row["row_count"] or 0),
        }
        for row in conn.execute(
            """
            SELECT projection_id, projection_fingerprint, COUNT(*) AS row_count
            FROM document_processing_state
            WHERE projection_id IS NOT NULL AND projection_id != ''
            GROUP BY projection_id, projection_fingerprint
            ORDER BY row_count DESC, projection_id
            """
        ).fetchall()
    ]


def slot_coverage(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "slot": str(row["slot"] or ""),
            "count": int(row["row_count"] or 0),
            "projection_backed_count": int(row["projection_backed_count"] or 0),
        }
        for row in conn.execute(
            """
            SELECT slot, COUNT(*) AS row_count, SUM(CASE WHEN COALESCE(is_projection_backed, 0) = 1 THEN 1 ELSE 0 END) AS projection_backed_count
            FROM slot_candidates
            GROUP BY slot
            ORDER BY row_count DESC, slot
            """
        ).fetchall()
    ]


def promotion_coverage(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "slot": str(row["slot"] or ""),
            "slot_label": str(row["slot_label"] or ""),
            "value_type": str(row["value_type"] or ""),
            "query_role": str(row["query_role"] or ""),
            "document_count": int(row["document_count"] or 0),
            "value_count": int(row["value_count"] or 0),
            "candidate_backed_count": int(row["candidate_backed_count"] or 0),
        }
        for row in conn.execute(
            """
            SELECT
                slot,
                slot_label,
                value_type,
                query_role,
                COUNT(DISTINCT document_id) AS document_count,
                COUNT(*) AS value_count,
                SUM(CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) AS candidate_backed_count
            FROM document_promotions
            WHERE COALESCE(is_current, 1) = 1
            GROUP BY slot, slot_label, value_type, query_role
            ORDER BY document_count DESC, value_count DESC, slot
            """
        ).fetchall()
    ]


def affected_documents(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "document_id": str(row["id"] or ""),
            "file_name": str(row["file_name"] or ""),
            "validator_status": str(row["validator_status"] or ""),
            "validator_issues_count": int(row["validator_issues_count"] or 0),
            "needs_review": bool(row["needs_review"] or row["interpreter_needs_review"] or row["normalizer_needs_review"]),
            "projection_id": str(row["projection_id"] or ""),
        }
        for row in conn.execute(
            """
            SELECT id, file_name, validator_status, validator_issues_count, needs_review, interpreter_needs_review, normalizer_needs_review, projection_id
            FROM documents
            WHERE COALESCE(is_archived, 0) = 0
              AND (
                COALESCE(needs_review, 0) = 1
                OR COALESCE(interpreter_needs_review, 0) = 1
                OR COALESCE(normalizer_needs_review, 0) = 1
                OR COALESCE(validator_issues_count, 0) > 0
              )
            ORDER BY loaded_at DESC, id
            LIMIT 10
            """
        ).fetchall()
    ]


def issue_clusters(review_row, entity_row) -> list[dict[str, object]]:
    clusters = []
    if int(review_row["needs_review"] or 0):
        clusters.append({"cluster_code": "needs_review", "document_count": int(review_row["needs_review"] or 0)})
    if int(review_row["validator_issues"] or 0):
        clusters.append({"cluster_code": "validator_issues", "document_count": int(review_row["validator_issues"] or 0)})
    if int(entity_row["materialization_audits"] or 0):
        clusters.append({"cluster_code": "materialization_audit", "document_count": int(entity_row["materialization_audits"] or 0)})
    return clusters
