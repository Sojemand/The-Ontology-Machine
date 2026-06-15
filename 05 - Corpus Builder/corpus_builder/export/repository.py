"""Repository stage for corpus export DB reads."""

from __future__ import annotations

import json
import sqlite3

from ..database import (
    get_fields_dict,
    get_orgs_list,
    get_people_list,
    get_relations_list,
    get_rows_list,
    get_tags_list,
)
from .types import ExportDocumentSnapshot


def fetch_document_snapshots(
    conn: sqlite3.Connection,
    *,
    include_archived: bool = False,
) -> list[ExportDocumentSnapshot]:
    where = "" if include_archived else "WHERE d.is_archived = 0"
    rows = conn.execute(
        "SELECT d.*, "
        "dps.projection_id AS processing_projection_id, "
        "dps.projection_fingerprint AS processing_projection_fingerprint, "
        "dps.materialization_state AS processing_materialization_state, "
        "dps.materialization_version AS processing_materialization_version "
        "FROM documents d "
        "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
        f"{where}"
    ).fetchall()
    return [_hydrate_document_snapshot(conn, row) for row in rows]


def _hydrate_document_snapshot(
    conn: sqlite3.Connection,
    doc_row: sqlite3.Row,
) -> ExportDocumentSnapshot:
    doc_id = str(doc_row["id"])
    processing_state = _row_processing_state(doc_row)
    document_promotions = _fetch_document_promotions(conn, doc_id)
    return ExportDocumentSnapshot(
        id=doc_id,
        file_name=doc_row["file_name"],
        file_path=doc_row["file_path"],
        content_hash=doc_row["content_hash"],
        document_type=doc_row["document_type"],
        category=doc_row["category"],
        subcategory=doc_row["subcategory"],
        language=doc_row["language"],
        model_confidence=doc_row["model_confidence"],
        validator_status=doc_row["validator_status"],
        projection_id=processing_state["projection_id"] if processing_state else None,
        projection_fingerprint=processing_state["projection_fingerprint"] if processing_state else None,
        materialization_state=processing_state["materialization_state"] if processing_state else None,
        materialization_version=processing_state["materialization_version"] if processing_state else None,
        loaded_at=doc_row["loaded_at"],
        fields=get_fields_dict(conn, doc_id),
        rows=get_rows_list(conn, doc_id),
        relations=get_relations_list(conn, doc_id),
        tags=get_tags_list(conn, doc_id),
        people=get_people_list(conn, doc_id),
        organizations=get_orgs_list(conn, doc_id),
        entities=_fetch_entities(conn, doc_id),
        document_promotions=document_promotions,
        document_promotion_values=_document_promotion_values(document_promotions),
        processing_state=processing_state,
    )


def _fetch_entities(conn: sqlite3.Connection, doc_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT entity_key, entity_type, role_type, display_value, normalized_value, source_path, row_index, page, sequence, projection_id, materialization_version, state "
        "FROM document_entities WHERE document_id = ? ORDER BY entity_id",
        (doc_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_document_promotions(conn: sqlite3.Connection, doc_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT slot, slot_label, value_type, query_role, display_value, normalized_value, compact_value, numeric_value, date_value, value_json, ordinal, confidence, source_path, projection_id, release_fingerprint, materialization_version "
        "FROM document_promotions WHERE document_id = ? AND is_current = 1 ORDER BY slot, ordinal, promotion_id",
        (doc_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _document_promotion_values(promotions: list[dict]) -> dict[str, object]:
    result: dict[str, object] = {}
    for promotion in promotions:
        slot = str(promotion["slot"])
        value = _decoded_promotion_value(promotion)
        if slot in result:
            existing = result[slot]
            result[slot] = [*existing, value] if isinstance(existing, list) else [existing, value]
        else:
            result[slot] = value
    return result


def _decoded_promotion_value(promotion: dict) -> object:
    value_json = promotion.get("value_json")
    if value_json:
        try:
            return json.loads(str(value_json))
        except Exception:
            return value_json
    return promotion.get("display_value")


def _row_processing_state(doc_row: sqlite3.Row) -> dict | None:
    state = {
        "projection_id": doc_row["processing_projection_id"],
        "projection_fingerprint": doc_row["processing_projection_fingerprint"],
        "materialization_state": doc_row["processing_materialization_state"],
        "materialization_version": doc_row["processing_materialization_version"],
    }
    return state if any(value not in (None, "") for value in state.values()) else None
