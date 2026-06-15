"""Persistence helpers for the loader pipeline."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..models.serialization import now_iso
from .fts_repository import archive_document, insert_fts_entry, remove_from_fts
from .policy import compact_search_text, detect_field_type, is_non_empty, normalize_search_text
from .semantic_repository import (
    build_semantic_evidence_index,
    clear_semantic_materialization,
    insert_document_entities,
    insert_document_promotion,
    insert_materialization_audits,
    insert_processing_state,
)
from .types import DOCUMENT_COLUMNS, NORMALIZED_TABLE_COLUMNS, JsonDict


def _sqlite_safe(value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value


def insert_document(conn: sqlite3.Connection, doc: JsonDict) -> None:
    placeholders = ", ".join(["?"] * len(DOCUMENT_COLUMNS))
    conn.execute(f"INSERT INTO documents ({', '.join(DOCUMENT_COLUMNS)}) VALUES ({placeholders})", [_sqlite_safe(doc.get(column)) for column in DOCUMENT_COLUMNS])


def insert_document_payload(
    conn: sqlite3.Connection,
    doc_id: str,
    structured_json: JsonDict | None,
    normalized_json: JsonDict | None = None,
    *,
    raw_json: JsonDict | None = None,
    release_fingerprint: str | None = None,
    free_text: str | None = None,
    original_file_name: str | None = None,
    original_media_type: str | None = None,
    original_blob: bytes | None = None,
) -> None:
    structured_payload = structured_json if isinstance(structured_json, dict) else {}
    preferred_payload = normalized_json if isinstance(normalized_json, dict) else structured_payload
    content = preferred_payload.get("content") if isinstance(preferred_payload.get("content"), dict) else {}
    projection = preferred_payload.get("projection") if preferred_payload.get("projection") is not None else structured_payload.get("projection")
    conn.execute(
        "INSERT INTO document_payloads (document_id, schema_version, structured_json, raw_json, normalized_json, projection_json, original_file_name, original_media_type, original_blob, release_fingerprint, free_text, loaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            structured_payload.get("schema_version") or preferred_payload.get("schema_version"),
            json.dumps(structured_payload, ensure_ascii=False),
            json.dumps(raw_json, ensure_ascii=False) if isinstance(raw_json, dict) else None,
            json.dumps(normalized_json, ensure_ascii=False) if normalized_json is not None else None,
            json.dumps(projection, ensure_ascii=False) if projection is not None else None,
            original_file_name,
            original_media_type,
            sqlite3.Binary(original_blob) if isinstance(original_blob, (bytes, bytearray)) else None,
            release_fingerprint,
            free_text if is_non_empty(free_text) else content.get("free_text") if is_non_empty(content.get("free_text")) else None,
            now_iso(),
        ),
    )


def insert_evidence_atom(conn: sqlite3.Connection, doc_id: str, atom: JsonDict) -> int:
    cursor = conn.execute("INSERT INTO evidence_atoms (document_id, atom_type, json_path, anchor_kind, anchor_key, page, row_index, column_key, source_ref, text_value, normalized_text, compact_text, numeric_value, date_value, currency, context_label, context_window) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (doc_id, atom.get("atom_type"), atom.get("json_path"), atom.get("anchor_kind"), atom.get("anchor_key"), atom.get("page"), atom.get("row_index"), atom.get("column_key"), atom.get("source_ref"), atom.get("text_value"), atom.get("normalized_text"), atom.get("compact_text"), atom.get("numeric_value"), atom.get("date_value"), atom.get("currency"), atom.get("context_label"), atom.get("context_window")))
    return int(cursor.lastrowid)


def insert_slot_candidate(conn: sqlite3.Connection, doc_id: str, candidate: JsonDict) -> int:
    cursor = conn.execute("INSERT INTO slot_candidates (document_id, slot, display_value, normalized_value, compact_value, numeric_value, date_value, strategy, confidence, ambiguity_group, is_projection_backed, candidate_layer, candidate_origin, source_refs_json, origin_path, origin_kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (doc_id, candidate.get("slot"), candidate.get("display_value"), candidate.get("normalized_value"), candidate.get("compact_value"), candidate.get("numeric_value"), candidate.get("date_value"), candidate.get("strategy"), candidate.get("confidence"), candidate.get("ambiguity_group"), candidate.get("is_projection_backed", 0), candidate.get("candidate_layer") or "base", candidate.get("candidate_origin") or candidate.get("origin_kind") or candidate.get("strategy"), json.dumps(candidate.get("source_refs") or [], ensure_ascii=False), candidate.get("origin_path"), candidate.get("origin_kind")))
    return int(cursor.lastrowid)


def insert_candidate_evidence(conn: sqlite3.Connection, candidate_id: int, atom_id: int) -> None:
    conn.execute("INSERT OR IGNORE INTO candidate_evidence (candidate_id, atom_id) VALUES (?, ?)", (candidate_id, atom_id))


def clear_incoming_document_links(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute("DELETE FROM relations WHERE target_document_id = ?", (document_id,))
    conn.execute(
        "DELETE FROM semantic_evidence_links WHERE subject_kind = 'entity_relation' "
        "AND subject_id IN (SELECT relation_id FROM entity_relations WHERE target_document_id = ?)",
        (document_id,),
    )
    conn.execute("DELETE FROM entity_relations WHERE target_document_id = ?", (document_id,))


def insert_field(conn: sqlite3.Connection, doc_id: str, key: str, value: Any, *, confidence: str | None = None, source: str | None = None) -> None:
    value_str = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    value_type, numeric_value = detect_field_type(key, value)
    conn.execute("INSERT INTO extracted_fields (document_id, key, value, value_type, numeric_value, confidence, source, normalized_value, compact_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (doc_id, key, value_str, value_type, numeric_value, confidence, source, normalize_search_text(value_str), compact_search_text(value_str)))


def insert_row(conn: sqlite3.Connection, doc_id: str, row_index: int, row: JsonDict) -> None:
    conn.execute("INSERT INTO extracted_rows (document_id, row_index, row_json) VALUES (?, ?, ?)", (doc_id, row_index, json.dumps(row, ensure_ascii=False)))


def insert_relation(conn: sqlite3.Connection, doc_id: str, relation: JsonDict) -> None:
    target_hint = str(relation.get("target_hint") or relation.get("target") or "")
    conn.execute(
        "INSERT INTO relations (document_id, relation_type, target_hint, target_document_id, description, relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc_id,
            str(relation.get("type", "")),
            target_hint,
            _sqlite_safe(relation.get("target_document_id") or relation.get("target_id")),
            _sqlite_safe(relation.get("description")),
            relation.get("relation_origin") or "observed",
            relation.get("confidence"),
            _sqlite_safe(relation.get("evidence_refs") or "relations"),
            relation.get("inference_policy_version"),
            relation.get("status") or "observed",
            relation.get("created_by") or "corpus_builder",
            relation.get("created_at") or now_iso(),
        ),
    )


def insert_normalized(conn: sqlite3.Connection, table: str, doc_id: str, value: str) -> None:
    column, normalized_column, compact_column = NORMALIZED_TABLE_COLUMNS[table]
    conn.execute(f"INSERT OR IGNORE INTO {table} (document_id, {column}, {normalized_column}, {compact_column}) VALUES (?, ?, ?, ?)", (doc_id, value, normalize_search_text(value), compact_search_text(value)))


def log_history(conn: sqlite3.Connection, doc_id: str, action: str, *, old_hash: str | None = None, new_hash: str | None = None, details: str | None = None) -> None:
    conn.execute("INSERT INTO load_history (document_id, action, old_hash, new_hash, timestamp, details) VALUES (?, ?, ?, ?, ?, ?)", (doc_id, action, old_hash, new_hash, now_iso(), details))


__all__ = [
    "archive_document",
    "build_semantic_evidence_index",
    "clear_incoming_document_links",
    "clear_semantic_materialization",
    "insert_candidate_evidence",
    "insert_document",
    "insert_document_entities",
    "insert_document_payload",
    "insert_document_promotion",
    "insert_evidence_atom",
    "insert_field",
    "insert_fts_entry",
    "insert_materialization_audits",
    "insert_normalized",
    "insert_processing_state",
    "insert_relation",
    "insert_row",
    "insert_slot_candidate",
    "log_history",
    "remove_from_fts",
]
