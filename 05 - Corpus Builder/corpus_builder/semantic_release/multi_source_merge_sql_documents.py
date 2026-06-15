from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from .multi_source_merge_sql_helpers import insert_row, table_exists


def copy_documents(
    source_rows: Sequence[sqlite3.Row],
    target_conn: sqlite3.Connection,
    target_artifact_root: Path,
    doc_map: Mapping[str, str],
    doc_mappings: Mapping[str, Mapping[str, Any]],
    source_doc_map: Mapping[str, str],
) -> None:
    for row in source_rows:
        source_document_id = str(row["id"])
        mapping = doc_mappings[source_document_id]
        overrides = {
            "id": doc_map[source_document_id],
            "file_path": str(target_artifact_root / str(mapping.get("target_artifact_path") or "")),
        }
        if "source_file_path" in row.keys():
            overrides["source_file_path"] = overrides["file_path"]
        if "source_document_id" in row.keys():
            source_doc_id = str(row["source_document_id"] or "")
            if source_doc_id in source_doc_map:
                overrides["source_document_id"] = source_doc_map[source_doc_id]
        insert_row(target_conn, "documents", row, overrides=overrides)


def copy_document_keyed_tables(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_document_ids: Sequence[str],
    doc_map: Mapping[str, str],
) -> dict[str, dict[int, int]]:
    generated_maps: dict[str, dict[int, int]] = {"field": {}, "row": {}}
    for table, skip_columns in DOCUMENT_KEYED_TABLE_SPECS:
        if not table_exists(source_conn, table) or not table_exists(target_conn, table):
            continue
        for source_document_id in source_document_ids:
            for row in source_conn.execute(f"SELECT * FROM {table} WHERE document_id = ?", (source_document_id,)).fetchall():
                overrides: dict[str, Any] = {"document_id": doc_map[source_document_id]}
                if table == "embedding_chunks":
                    overrides["chunk_id"] = f"{doc_map[source_document_id]}__{row['chunk_id']}"
                cursor = insert_row(target_conn, table, row, skip_columns=skip_columns, overrides=overrides)
                if table == "extracted_fields":
                    generated_maps["field"][int(row["id"])] = int(cursor.lastrowid)
                elif table == "extracted_rows":
                    generated_maps["row"][int(row["id"])] = int(cursor.lastrowid)
    return generated_maps


def copy_generated_id_table(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table: str,
    id_column: str,
    source_document_ids: Sequence[str],
    doc_map: Mapping[str, str],
) -> dict[int, int]:
    id_map: dict[int, int] = {}
    if not table_exists(source_conn, table) or not table_exists(target_conn, table):
        return id_map
    for source_document_id in source_document_ids:
        for row in source_conn.execute(f"SELECT * FROM {table} WHERE document_id = ?", (source_document_id,)).fetchall():
            cursor = insert_row(target_conn, table, row, skip_columns=(id_column,), overrides={"document_id": doc_map[source_document_id]})
            id_map[int(row[id_column])] = int(cursor.lastrowid)
    return id_map


def copy_candidate_evidence(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    candidate_map: Mapping[int, int],
    atom_map: Mapping[int, int],
) -> None:
    if not candidate_map or not atom_map or not table_exists(source_conn, "candidate_evidence"):
        return
    for row in source_conn.execute("SELECT * FROM candidate_evidence").fetchall():
        candidate_id = candidate_map.get(int(row["candidate_id"]))
        atom_id = atom_map.get(int(row["atom_id"]))
        if candidate_id is not None and atom_id is not None:
            target_conn.execute("INSERT OR IGNORE INTO candidate_evidence (candidate_id, atom_id) VALUES (?, ?)", (candidate_id, atom_id))


def copy_document_promotions(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_document_ids: Sequence[str],
    doc_map: Mapping[str, str],
    candidate_map: Mapping[int, int],
) -> dict[int, int]:
    promotion_map: dict[int, int] = {}
    if not table_exists(source_conn, "document_promotions") or not table_exists(target_conn, "document_promotions"):
        return promotion_map
    for source_document_id in source_document_ids:
        for row in source_conn.execute("SELECT * FROM document_promotions WHERE document_id = ? ORDER BY promotion_id", (source_document_id,)).fetchall():
            overrides: dict[str, Any] = {"document_id": doc_map[source_document_id]}
            if "candidate_id" in row.keys() and row["candidate_id"] is not None:
                overrides["candidate_id"] = candidate_map.get(int(row["candidate_id"]))
            cursor = insert_row(target_conn, "document_promotions", row, skip_columns=("promotion_id",), overrides=overrides)
            promotion_map[int(row["promotion_id"])] = int(cursor.lastrowid)
    return promotion_map


DOCUMENT_KEYED_TABLE_SPECS = (
    ("document_payloads", ()),
    ("extracted_fields", ("id",)),
    ("extracted_rows", ("id",)),
    ("tags", ()),
    ("people", ()),
    ("organizations", ()),
    ("document_page_images", ()),
    ("embeddings", ()),
    ("embedding_chunks", ()),
    ("document_processing_state", ()),
    ("materialization_audit", ("audit_id",)),
    ("load_history", ("id",)),
)
