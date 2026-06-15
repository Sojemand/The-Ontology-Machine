from __future__ import annotations

import sqlite3
from typing import Mapping, Sequence

from .multi_source_merge_sql_helpers import insert_row, table_exists
from .multi_source_merge_sql_refs import merged_id, rewrite_json_text
from .sql_parameter_batches import iter_parameter_batches


def copy_source_documents(source_conn, target_conn, source_ids, source_doc_map, doc_map, replacements) -> int:
    if not table_exists(source_conn, "source_documents") or not table_exists(target_conn, "source_documents"):
        return 0
    count = 0
    for row in fetch_rows_by_source_documents(source_conn, "source_documents", source_ids, "source_document_id"):
        first_document_id = doc_map.get(str(row["first_document_id"] or ""))
        last_document_id = doc_map.get(str(row["last_document_id"] or ""))
        if not first_document_id or not last_document_id:
            continue
        insert_row(
            target_conn,
            "source_documents",
            row,
            overrides={
                "source_document_id": source_doc_map[str(row["source_document_id"])],
                "first_document_id": first_document_id,
                "last_document_id": last_document_id,
                "metadata_json": rewrite_json_text(row["metadata_json"], replacements),
            },
        )
        count += 1
    return count


def copy_source_document_pages(source_conn, target_conn, source_ids, source_doc_map, doc_map, replacements) -> int:
    if not table_exists(source_conn, "source_document_pages") or not table_exists(target_conn, "source_document_pages"):
        return 0
    count = 0
    for row in fetch_rows_by_source_documents(source_conn, "source_document_pages", source_ids, "source_document_id"):
        document_id = doc_map.get(str(row["document_id"] or ""))
        if not document_id:
            continue
        insert_row(
            target_conn,
            "source_document_pages",
            row,
            overrides={
                "source_document_id": source_doc_map[str(row["source_document_id"])],
                "document_id": document_id,
                "prev_document_id": doc_map.get(str(row["prev_document_id"] or "")),
                "next_document_id": doc_map.get(str(row["next_document_id"] or "")),
                "evidence_json": rewrite_json_text(row["evidence_json"], replacements),
            },
        )
        count += 1
    return count


def copy_source_document_classifications(
    source_conn,
    target_conn,
    source_ids,
    source_doc_map,
    *,
    ontology_map: Mapping[str, str] | None,
) -> int:
    if not table_exists(source_conn, "source_document_classifications") or not table_exists(target_conn, "source_document_classifications"):
        return 0
    count = 0
    for row in fetch_rows_by_source_documents(source_conn, "source_document_classifications", source_ids, "source_document_id"):
        ontology_id = row["ontology_id"]
        if ontology_map is None and ontology_id is not None:
            continue
        if ontology_map is not None:
            if ontology_id is None:
                continue
            ontology_id = ontology_map.get(str(ontology_id))
            if not ontology_id:
                continue
        insert_row(
            target_conn,
            "source_document_classifications",
            row,
            overrides={
                "source_document_id": source_doc_map[str(row["source_document_id"])],
                "ontology_id": ontology_id,
            },
        )
        count += 1
    return count


def copy_structural_units(target_conn, rows, source_doc_map, doc_map, unit_map, replacements) -> int:
    pending = {str(row["unit_id"]): row for row in rows}
    inserted: set[str] = set()
    count = 0
    while pending:
        progressed = False
        for unit_id, row in list(pending.items()):
            parent_id = str(row["parent_unit_id"] or "")
            if parent_id and parent_id in pending and parent_id not in inserted:
                continue
            insert_row(
                target_conn,
                "structural_units",
                row,
                overrides={
                    "unit_id": unit_map[unit_id],
                    "source_document_id": source_doc_map[str(row["source_document_id"])],
                    "parent_unit_id": unit_map.get(parent_id) if parent_id else None,
                    "document_id": doc_map.get(str(row["document_id"] or "")),
                    "metadata_json": rewrite_json_text(row["metadata_json"], replacements),
                },
            )
            inserted.add(unit_id)
            pending.pop(unit_id)
            count += 1
            progressed = True
        if not progressed:
            raise ValueError("base_graph_invalid: structural_units contain a parent cycle.")
    return count


def copy_structural_unit_relations(
    source_conn,
    target_conn,
    source_ids,
    source_doc_map,
    unit_map,
    replacements,
    *,
    merge_run_id: str,
    source_database_id: str,
) -> int:
    if not table_exists(source_conn, "structural_unit_relations") or not table_exists(target_conn, "structural_unit_relations"):
        return 0
    count = 0
    for row in fetch_rows_by_source_documents(source_conn, "structural_unit_relations", source_ids, "source_document_id"):
        source_unit_id = unit_map.get(str(row["source_unit_id"] or ""))
        target_unit_id = unit_map.get(str(row["target_unit_id"] or ""))
        if not source_unit_id or not target_unit_id:
            continue
        insert_row(
            target_conn,
            "structural_unit_relations",
            row,
            overrides={
                "relation_id": merged_id("mrg_sur", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["relation_id"]),
                "source_document_id": source_doc_map[str(row["source_document_id"])],
                "source_unit_id": source_unit_id,
                "target_unit_id": target_unit_id,
                "evidence_json": rewrite_json_text(row["evidence_json"], replacements),
            },
        )
        count += 1
    return count


def fetch_rows_by_source_documents(
    conn: sqlite3.Connection,
    table: str,
    source_ids: Sequence[str],
    column: str,
) -> list[sqlite3.Row]:
    if not source_ids or not table_exists(conn, table):
        return []
    rows: list[sqlite3.Row] = []
    for batch in iter_parameter_batches(source_ids):
        placeholders = ", ".join("?" for _ in batch)
        rows.extend(conn.execute(f"SELECT * FROM {table} WHERE {column} IN ({placeholders})", batch).fetchall())
    return rows

