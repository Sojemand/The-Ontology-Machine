"""Low-level row copy helpers for corpus document merges."""

from __future__ import annotations

import sqlite3
from typing import Any

from .merge_entity_rows import (
    copy_document_entities,
    copy_entity_attributes,
    copy_entity_relations,
    copy_semantic_evidence_links,
)
from .merge_row_sql import insert_dynamic_row, rewrite_document_targets
from .sql_parameter_batches import iter_parameter_batches


def copy_optional_single_row(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    value: str,
    *,
    replace_values: dict[str, Any] | None = None,
) -> None:
    row = source_conn.execute(f"SELECT * FROM {table_name} WHERE {column_name} = ? LIMIT 1", (value,)).fetchone()
    if row is not None:
        payload = dict(row)
        payload.update(replace_values or {})
        insert_dynamic_row(target_conn, table_name, payload)


def copy_simple_rows(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    value: str,
    *,
    exclude_columns: set[str] | None = None,
    replace_values: dict[str, Any] | None = None,
    relation_target_rewrite_map: dict[str, str] | None = None,
) -> None:
    rows = source_conn.execute(f"SELECT * FROM {table_name} WHERE {column_name} = ? ORDER BY rowid", (value,)).fetchall()
    for row in rows:
        payload = dict(row)
        for excluded in exclude_columns or set():
            payload.pop(excluded, None)
        payload.update(replace_values or {})
        rewrite_document_targets(payload, relation_target_rewrite_map)
        insert_dynamic_row(target_conn, table_name, payload)


def copy_evidence_atoms(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    rows = source_conn.execute("SELECT * FROM evidence_atoms WHERE document_id = ? ORDER BY atom_id", (document_id,)).fetchall()
    for row in rows:
        payload = dict(row)
        old_id = int(payload.pop("atom_id"))
        payload["document_id"] = target_document_id
        mapping[old_id] = insert_dynamic_row(target_conn, "evidence_atoms", payload)
    return mapping


def copy_slot_candidates(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    rows = source_conn.execute("SELECT * FROM slot_candidates WHERE document_id = ? ORDER BY candidate_id", (document_id,)).fetchall()
    for row in rows:
        payload = dict(row)
        old_id = int(payload.pop("candidate_id"))
        payload["document_id"] = target_document_id
        mapping[old_id] = insert_dynamic_row(target_conn, "slot_candidates", payload)
    return mapping


def copy_candidate_evidence(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    atom_map: dict[int, int],
    candidate_map: dict[int, int],
) -> None:
    if not atom_map or not candidate_map:
        return
    for candidate_ids in iter_parameter_batches(candidate_map):
        placeholders = ", ".join("?" for _ in candidate_ids)
        rows = source_conn.execute(
            f"SELECT candidate_id, atom_id FROM candidate_evidence WHERE candidate_id IN ({placeholders}) ORDER BY candidate_id, atom_id",
            candidate_ids,
        )
        for row in rows:
            target_conn.execute(
                "INSERT INTO candidate_evidence (candidate_id, atom_id) VALUES (?, ?)",
                (candidate_map[int(row["candidate_id"])], atom_map[int(row["atom_id"])]),
            )


def copy_document_promotions(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    document_id: str,
    *,
    target_document_id: str,
    candidate_map: dict[int, int],
) -> None:
    rows = source_conn.execute("SELECT * FROM document_promotions WHERE document_id = ? ORDER BY promotion_id", (document_id,)).fetchall()
    for row in rows:
        payload = dict(row)
        payload.pop("promotion_id", None)
        payload["document_id"] = target_document_id
        if payload.get("candidate_id") is not None:
            payload["candidate_id"] = candidate_map.get(int(payload["candidate_id"]))
        insert_dynamic_row(target_conn, "document_promotions", payload)
