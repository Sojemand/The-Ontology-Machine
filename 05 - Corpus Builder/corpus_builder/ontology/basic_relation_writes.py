from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from .basic_relation_support import DocumentRow


def clear_base_graph(conn: sqlite3.Connection, current_source_document_ids: Iterable[str] | None = None) -> None:
    conn.execute("DELETE FROM structural_unit_relations WHERE relation_origin = 'base_graph' OR created_by = 'basic_relation_mining'")
    conn.execute("DELETE FROM structural_units WHERE unit_origin = 'base_graph' OR created_by = 'basic_relation_mining'")
    conn.execute(
        "DELETE FROM source_document_classifications "
        "WHERE classification_scope IN ('base', 'semantic_release') "
        "AND (created_by = 'basic_relation_mining' OR ontology_id IS NULL)"
    )
    conn.execute("DELETE FROM source_document_pages")
    conn.execute("DELETE FROM relations WHERE relation_origin = 'base_graph' OR created_by = 'basic_relation_mining'")
    _delete_stale_source_documents(conn, current_source_document_ids)


def insert_source_document(conn: sqlite3.Connection, group: list[DocumentRow]) -> None:
    first = group[0]
    last = group[-1]
    conn.execute(
        "INSERT INTO source_documents (source_document_id, source_uri, source_file_id, source_artifact_id, "
        "ingest_run_id, source_title, source_kind, page_count, first_document_id, last_document_id, "
        "source_content_hash, metadata_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
        "ON CONFLICT(source_document_id) DO UPDATE SET "
        "source_uri = excluded.source_uri, "
        "source_file_id = excluded.source_file_id, "
        "source_artifact_id = excluded.source_artifact_id, "
        "ingest_run_id = excluded.ingest_run_id, "
        "source_title = excluded.source_title, "
        "source_kind = excluded.source_kind, "
        "page_count = excluded.page_count, "
        "first_document_id = excluded.first_document_id, "
        "last_document_id = excluded.last_document_id, "
        "source_content_hash = excluded.source_content_hash, "
        "metadata_json = excluded.metadata_json, "
        "updated_at = CURRENT_TIMESTAMP",
        (
            first.source_document_id,
            first.source_uri,
            first.source_file_id,
            first.source_artifact_id,
            first.ingest_run_id,
            first.file_name,
            first.document_type,
            len(group),
            first.document_id,
            last.document_id,
            first.source_content_hash,
            json.dumps({"materialized_by": "basic_relation_mining"}, ensure_ascii=False),
        ),
    )


def insert_source_document_pages(conn: sqlite3.Connection, group: list[DocumentRow]) -> None:
    for index, document in enumerate(group):
        prev_document_id = group[index - 1].document_id if index > 0 else None
        next_document_id = group[index + 1].document_id if index + 1 < len(group) else None
        conn.execute(
            "INSERT INTO source_document_pages (source_document_id, document_id, page_index, page_label, "
            "prev_document_id, next_document_id, confidence, evidence_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1.0, ?, CURRENT_TIMESTAMP)",
            (
                document.source_document_id,
                document.document_id,
                document.page_index,
                document.page_label,
                prev_document_id,
                next_document_id,
                json.dumps({"basis": "documents.source_document_id/page_index"}, ensure_ascii=False),
            ),
        )


def insert_relations(conn: sqlite3.Connection, group: list[DocumentRow]) -> int:
    inserted = 0
    for index, document in enumerate(group):
        conn.execute(
            "INSERT INTO relations (document_id, relation_type, target_hint, target_document_id, description, "
            "relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at) "
            "VALUES (?, 'page_of_source_document', ?, NULL, ?, 'base_graph', 1.0, ?, NULL, 'materialized', 'basic_relation_mining', CURRENT_TIMESTAMP)",
            (
                document.document_id,
                document.source_document_id,
                "Page belongs to deterministic source document.",
                json.dumps({"source_document_id": document.source_document_id}, ensure_ascii=False),
            ),
        )
        inserted += 1
        inserted += _insert_neighbor_relation(conn, group, index, "next_page", 1)
        inserted += _insert_neighbor_relation(conn, group, index, "previous_page", -1)
    return inserted


def _insert_neighbor_relation(
    conn: sqlite3.Connection,
    group: list[DocumentRow],
    index: int,
    relation_type: str,
    offset: int,
) -> int:
    target_index = index + offset
    if target_index < 0 or target_index >= len(group):
        return 0
    document = group[index]
    target = group[target_index]
    description = "Next page in deterministic source document order." if offset > 0 else "Previous page in deterministic source document order."
    conn.execute(
        "INSERT INTO relations (document_id, relation_type, target_hint, target_document_id, description, "
        "relation_origin, confidence, evidence_refs, inference_policy_version, status, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'base_graph', 1.0, ?, NULL, 'materialized', 'basic_relation_mining', CURRENT_TIMESTAMP)",
        (
            document.document_id,
            relation_type,
            target.document_id,
            target.document_id,
            description,
            json.dumps({"source_document_id": document.source_document_id}, ensure_ascii=False),
        ),
    )
    return 1


def _delete_stale_source_documents(conn: sqlite3.Connection, current_source_document_ids: Iterable[str] | None) -> None:
    if current_source_document_ids is None:
        conn.execute("DELETE FROM source_documents")
        return
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS tmp_basic_relation_current_source_documents "
        "(source_document_id TEXT PRIMARY KEY)"
    )
    conn.execute("DELETE FROM tmp_basic_relation_current_source_documents")
    conn.executemany(
        "INSERT OR IGNORE INTO tmp_basic_relation_current_source_documents (source_document_id) VALUES (?)",
        ((source_document_id,) for source_document_id in sorted(set(current_source_document_ids)) if source_document_id),
    )
    conn.execute(
        "DELETE FROM source_documents "
        "WHERE source_document_id NOT IN (SELECT source_document_id FROM tmp_basic_relation_current_source_documents)"
    )
    conn.execute("DELETE FROM tmp_basic_relation_current_source_documents")


__all__ = [
    "clear_base_graph",
    "insert_relations",
    "insert_source_document",
    "insert_source_document_pages",
]
