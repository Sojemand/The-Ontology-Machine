"""Core semantic materialization writes."""

from __future__ import annotations

import json
import sqlite3

from ..models.serialization import now_iso
from .semantic_repository_evidence import _delete_materialized_semantic_evidence_links
from .types import JsonDict


def clear_semantic_materialization(conn: sqlite3.Connection, document_id: str) -> None:
    _delete_materialized_semantic_evidence_links(conn, document_id)
    conn.execute("UPDATE document_promotions SET is_current = 0 WHERE document_id = ? AND is_current = 1", (document_id,))
    conn.execute("DELETE FROM candidate_evidence WHERE candidate_id IN (SELECT candidate_id FROM slot_candidates WHERE document_id = ?)", (document_id,))
    for table in ("slot_candidates", "materialization_audit", "document_processing_state"):
        conn.execute(f"DELETE FROM {table} WHERE document_id = ?", (document_id,))
    conn.execute(
        "DELETE FROM entity_relations WHERE document_id = ? AND (relation_origin = 'materialized' OR status = 'materialized' OR created_by = 'semantic_release' OR source_entity_id IN (SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized') OR target_entity_id IN (SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized'))",
        (document_id, document_id, document_id),
    )
    conn.execute("DELETE FROM document_entities WHERE document_id = ? AND state = 'materialized'", (document_id,))


def insert_processing_state(conn: sqlite3.Connection, state: JsonDict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO document_processing_state "
        "(document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id, projection_fingerprint, "
        "materialization_state, stale_reason, source_mode, last_materialized_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            state.get("document_id"),
            state.get("schema_version"),
            state.get("materialization_version"),
            state.get("materialized_snapshot_id"),
            state.get("projection_id"),
            state.get("projection_fingerprint"),
            state.get("materialization_state"),
            state.get("stale_reason"),
            state.get("source_mode"),
            state.get("last_materialized_at"),
        ),
    )


def insert_document_promotion(conn: sqlite3.Connection, document_id: str, promotion: JsonDict, *, candidate_id: int | None = None) -> int:
    cursor = conn.execute(
        "INSERT INTO document_promotions "
        "(document_id, slot, slot_label, value_type, query_role, display_value, normalized_value, compact_value, numeric_value, date_value, "
        "value_json, ordinal, confidence, candidate_id, source_path, source_refs_json, projection_id, release_fingerprint, "
        "materialization_version, is_current, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (
            document_id,
            promotion.get("slot"),
            promotion.get("slot_label"),
            promotion.get("value_type") or "string",
            promotion.get("query_role"),
            promotion.get("display_value"),
            promotion.get("normalized_value"),
            promotion.get("compact_value"),
            promotion.get("numeric_value"),
            promotion.get("date_value"),
            promotion.get("value_json"),
            promotion.get("ordinal") or 0,
            promotion.get("confidence"),
            candidate_id,
            promotion.get("source_path"),
            json.dumps(promotion.get("source_refs") or [], ensure_ascii=False),
            promotion.get("projection_id"),
            promotion.get("release_fingerprint"),
            promotion.get("materialization_version"),
            now_iso(),
        ),
    )
    return int(cursor.lastrowid)


def insert_materialization_audits(conn: sqlite3.Connection, document_id: str, audits: list[JsonDict]) -> None:
    for audit in audits:
        conn.execute(
            "INSERT INTO materialization_audit (created_at, level, code, document_id, projection_id, message, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), audit.get("level") or "info", audit.get("code") or "semantic_audit", document_id, audit.get("projection_id"), audit.get("message") or "", audit.get("details_json")),
        )
