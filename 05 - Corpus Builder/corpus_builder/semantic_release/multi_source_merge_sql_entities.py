from __future__ import annotations

import sqlite3
from typing import Any, Mapping, Sequence

from .multi_source_merge_sql_helpers import insert_row, optional_int_map, table_exists
from .multi_source_merge_sql_refs import rewrite_json_text, stringify_map
from .sql_parameter_batches import iter_parameter_batches


def copy_entity_attributes(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    entity_map: Mapping[int, int],
) -> dict[int, int]:
    attribute_map: dict[int, int] = {}
    if not entity_map or not table_exists(source_conn, "entity_attributes"):
        return attribute_map
    for row in source_conn.execute("SELECT * FROM entity_attributes").fetchall():
        entity_id = entity_map.get(int(row["entity_id"]))
        if entity_id is not None:
            cursor = insert_row(target_conn, "entity_attributes", row, skip_columns=("attribute_id",), overrides={"entity_id": entity_id})
            attribute_map[int(row["attribute_id"])] = int(cursor.lastrowid)
    return attribute_map


def copy_entity_relations(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    entity_map: Mapping[int, int],
    doc_map: Mapping[str, str],
    source_document_ids: Sequence[str],
) -> dict[int, int]:
    relation_map: dict[int, int] = {}
    if not table_exists(source_conn, "entity_relations"):
        return relation_map
    for source_document_id in source_document_ids:
        for row in source_conn.execute("SELECT * FROM entity_relations WHERE document_id = ?", (source_document_id,)).fetchall():
            overrides = {
                "document_id": doc_map[source_document_id],
                "source_entity_id": optional_int_map(entity_map, row["source_entity_id"]),
                "target_entity_id": optional_int_map(entity_map, row["target_entity_id"]),
                "target_document_id": doc_map.get(str(row["target_document_id"] or ""), row["target_document_id"]),
            }
            cursor = insert_row(target_conn, "entity_relations", row, skip_columns=("relation_id",), overrides=overrides)
            relation_map[int(row["relation_id"])] = int(cursor.lastrowid)
    return relation_map


def copy_semantic_evidence_links(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    atom_map: Mapping[int, int],
    entity_map: Mapping[int, int],
    attribute_map: Mapping[int, int],
    relation_map: Mapping[int, int],
) -> None:
    if not atom_map or not table_exists(source_conn, "semantic_evidence_links"):
        return
    subject_maps: dict[str, Mapping[int, int]] = {
        "document_entity": entity_map,
        "entity_attribute": attribute_map,
        "entity_relation": relation_map,
    }
    for subject_kind, subject_map in subject_maps.items():
        if not subject_map:
            continue
        for subject_ids in iter_parameter_batches(subject_map, reserved_parameters=1):
            placeholders = ", ".join("?" for _ in subject_ids)
            rows = source_conn.execute(
                f"SELECT subject_kind, subject_id, atom_id, evidence_role FROM semantic_evidence_links "
                f"WHERE subject_kind = ? AND subject_id IN ({placeholders})",
                (subject_kind, *subject_ids),
            )
            _insert_evidence_link_rows(target_conn, rows, atom_map, subject_map)


def copy_relations(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    doc_map: Mapping[str, str],
    source_doc_map: Mapping[str, str],
    unit_map: Mapping[str, str],
    source_document_ids: Sequence[str],
) -> dict[int, int]:
    relation_map: dict[int, int] = {}
    if not table_exists(source_conn, "relations"):
        return relation_map
    replacements = {
        **stringify_map(doc_map),
        **stringify_map(source_doc_map),
        **stringify_map(unit_map),
    }
    for source_document_id in source_document_ids:
        for row in source_conn.execute("SELECT * FROM relations WHERE document_id = ?", (source_document_id,)).fetchall():
            target_hint = row["target_hint"]
            if str(row["relation_origin"] or "") == "base_graph":
                target_hint = replacements.get(str(target_hint or ""), target_hint)
            cursor = insert_row(
                target_conn,
                "relations",
                row,
                skip_columns=("id",),
                overrides={
                    "document_id": doc_map[source_document_id],
                    "target_document_id": doc_map.get(str(row["target_document_id"] or ""), row["target_document_id"]),
                    "target_hint": target_hint,
                    "evidence_refs": rewrite_json_text(row["evidence_refs"], replacements),
                },
            )
            relation_map[int(row["id"])] = int(cursor.lastrowid)
    return relation_map


def copy_fts_content(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_document_ids: Sequence[str],
    doc_map: Mapping[str, str],
) -> None:
    if not table_exists(source_conn, "documents_fts_content") or not table_exists(target_conn, "documents_fts_content"):
        return
    for source_document_id in source_document_ids:
        rows = source_conn.execute("SELECT * FROM documents_fts_content WHERE document_id = ?", (source_document_id,)).fetchall()
        for row in rows:
            _insert_fts_row(target_conn, row, doc_map[source_document_id])


def _insert_evidence_link_rows(
    target_conn: sqlite3.Connection,
    rows: Sequence[sqlite3.Row],
    atom_map: Mapping[int, int],
    subject_map: Mapping[int, int],
) -> None:
    for row in rows:
        atom_id = atom_map.get(int(row["atom_id"]))
        subject_id = subject_map.get(int(row["subject_id"]))
        if atom_id is not None and subject_id is not None:
            target_conn.execute(
                "INSERT OR IGNORE INTO semantic_evidence_links (subject_kind, subject_id, atom_id, evidence_role) VALUES (?, ?, ?, ?)",
                (row["subject_kind"], subject_id, atom_id, row["evidence_role"]),
            )


def _insert_fts_row(target_conn: sqlite3.Connection, row: sqlite3.Row, target_document_id: str) -> None:
    values = [target_document_id, *(row[column] for column in FTS_COLUMNS)]
    cursor = target_conn.execute(
        "INSERT INTO documents_fts_content (document_id, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
        values,
    )
    if table_exists(target_conn, "documents_fts"):
        target_conn.execute(
            "INSERT INTO documents_fts(rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
            [cursor.lastrowid, *(row[column] for column in FTS_COLUMNS)],
        )


FTS_COLUMNS = (
    "content_free_text",
    "fields_text",
    "tags_text",
    "people_text",
    "orgs_text",
)
