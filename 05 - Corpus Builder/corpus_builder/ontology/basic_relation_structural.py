from __future__ import annotations

import json
import sqlite3

from .basic_relation_support import (
    DocumentRow,
    base_unit_id,
    page_unit_id,
    structural_relation_id,
)


def insert_structural_units(conn: sqlite3.Connection, group: list[DocumentRow]) -> tuple[int, int]:
    first = group[0]
    last = group[-1]
    base_id = base_unit_id(first.source_document_id)
    _insert_base_unit(conn, base_id, first, last)
    page_unit_ids = _insert_page_units(conn, group, base_id)
    sequence_relations = _insert_page_sequence_relations(conn, page_unit_ids)
    return 1 + len(page_unit_ids), len(page_unit_ids) + sequence_relations


def _insert_base_unit(conn: sqlite3.Connection, base_id: str, first: DocumentRow, last: DocumentRow) -> None:
    conn.execute(
        "INSERT INTO structural_units (unit_id, source_document_id, unit_type, parent_unit_id, document_id, "
        "page_index, page_label, ordinal, start_page_index, end_page_index, label, text_hash, metadata_json, "
        "unit_origin, confidence, status, created_by, created_at, updated_at) "
        "VALUES (?, ?, 'base_unit', NULL, NULL, NULL, NULL, 0, ?, ?, ?, ?, ?, "
        "'base_graph', 1.0, 'materialized', 'basic_relation_mining', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (
            base_id,
            first.source_document_id,
            first.page_index,
            last.page_index,
            first.file_name,
            first.source_content_hash,
            json.dumps(
                {
                    "basis": "source_documents",
                    "reserved_unit_types": ["chapter", "section", "page_span"],
                },
                ensure_ascii=False,
            ),
        ),
    )


def _insert_page_units(conn: sqlite3.Connection, group: list[DocumentRow], base_id: str) -> list[tuple[DocumentRow, str]]:
    page_unit_ids: list[tuple[DocumentRow, str]] = []
    for index, document in enumerate(group):
        unit_id = page_unit_id(document.document_id)
        page_unit_ids.append((document, unit_id))
        conn.execute(
            "INSERT INTO structural_units (unit_id, source_document_id, unit_type, parent_unit_id, document_id, "
            "page_index, page_label, ordinal, start_page_index, end_page_index, label, text_hash, metadata_json, "
            "unit_origin, confidence, status, created_by, created_at, updated_at) "
            "VALUES (?, ?, 'page_unit', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "'base_graph', 1.0, 'materialized', 'basic_relation_mining', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (
                unit_id,
                document.source_document_id,
                base_id,
                document.document_id,
                document.page_index,
                document.page_label,
                index,
                document.page_index,
                document.page_index,
                document.page_label or f"Page {document.page_index + 1}",
                document.page_content_hash,
                json.dumps({"basis": "source_document_pages", "document_id": document.document_id}, ensure_ascii=False),
            ),
        )
        _insert_unit_relation(conn, document.source_document_id, base_id, unit_id, "contains", index, "base_unit_contains_page_unit")
    return page_unit_ids


def _insert_page_sequence_relations(conn: sqlite3.Connection, page_unit_ids: list[tuple[DocumentRow, str]]) -> int:
    inserted = 0
    for index, (document, unit_id) in enumerate(page_unit_ids):
        if index + 1 < len(page_unit_ids):
            _insert_unit_relation(conn, document.source_document_id, unit_id, page_unit_ids[index + 1][1], "next", index, "page_unit_sequence")
            inserted += 1
        if index > 0:
            _insert_unit_relation(conn, document.source_document_id, unit_id, page_unit_ids[index - 1][1], "previous", index, "page_unit_sequence")
            inserted += 1
    return inserted


def _insert_unit_relation(
    conn: sqlite3.Connection,
    source_document_id: str,
    source_unit_id: str,
    target_unit_id: str,
    relation_type: str,
    ordinal: int,
    basis: str,
) -> None:
    conn.execute(
        "INSERT INTO structural_unit_relations (relation_id, source_document_id, source_unit_id, target_unit_id, "
        "relation_type, ordinal, relation_origin, confidence, evidence_json, status, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'base_graph', 1.0, ?, 'materialized', 'basic_relation_mining', CURRENT_TIMESTAMP)",
        (
            structural_relation_id(relation_type, source_unit_id, target_unit_id),
            source_document_id,
            source_unit_id,
            target_unit_id,
            relation_type,
            ordinal,
            json.dumps({"basis": basis}, ensure_ascii=False),
        ),
    )


__all__ = ["insert_structural_units"]
