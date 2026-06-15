from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..database import connect


def remove_database_records(database_path: Path, record_refs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    document_ids = _document_ids(record_refs)
    if not document_ids:
        raise ValueError("records_not_isolated: cleanup requires document_id-bearing record refs.")
    if not database_path.exists():
        raise ValueError(f"database_missing: cleanup database does not exist: {database_path}")
    conn = connect(str(database_path))
    try:
        if not _table_exists(conn, "documents"):
            raise ValueError("database_missing: cleanup target is not a Corpus Builder database.")
        conn.execute("PRAGMA foreign_keys=ON")
        existing = _existing_document_ids(conn, document_ids)
        if existing != document_ids:
            missing = sorted(document_ids - existing)
            raise ValueError(f"records_not_isolated: cleanup database is missing scoped records: {missing}")
        conn.execute("BEGIN IMMEDIATE")
        for document_id in sorted(document_ids):
            _remove_from_fts(conn, document_id)
        _delete_rows_for_documents(conn, sorted(document_ids))
        remaining = _count_documents(conn)
        remaining_embeddings = _count_rows(conn, "embeddings") + _count_rows(conn, "embedding_chunks")
        conn.commit()
        return {
            "removed_database_record_refs": [dict(item) for item in record_refs],
            "removed_database_record_count": len(document_ids),
            "post_cleanup_counts": {
                "documents": remaining,
                "embeddings": remaining_embeddings,
                "remaining_records": remaining,
            },
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _document_ids(record_refs: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        str(item.get("document_id") or "").strip()
        for item in record_refs
        if isinstance(item, Mapping) and str(item.get("document_id") or "").strip()
    }


def _existing_document_ids(conn: sqlite3.Connection, document_ids: set[str]) -> set[str]:
    existing: set[str] = set()
    for document_id in sorted(document_ids):
        row = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is not None:
            existing.add(str(row["id"]))
    return existing


def _delete_rows_for_documents(conn: sqlite3.Connection, document_ids: Sequence[str]) -> None:
    for document_id in document_ids:
        _delete_related_ids(conn, "candidate_evidence", "candidate_id", "slot_candidates", "candidate_id", document_id)
        _delete_related_ids(conn, "candidate_evidence", "atom_id", "evidence_atoms", "atom_id", document_id)
        _delete_related_ids(conn, "entity_attributes", "entity_id", "document_entities", "entity_id", document_id)
        if _table_exists(conn, "entity_relations"):
            conn.execute(
                "DELETE FROM entity_relations WHERE document_id = ? OR target_document_id = ?",
                (document_id, document_id),
            )
        if _table_exists(conn, "relations"):
            conn.execute(
                "DELETE FROM relations WHERE document_id = ? OR target_document_id = ?",
                (document_id, document_id),
            )
        for table in (
            "embedding_chunks",
            "embeddings",
            "materialization_audit",
            "document_entities",
            "document_processing_state",
            "evidence_atoms",
            "slot_candidates",
            "extracted_rows",
            "extracted_fields",
            "tags",
            "people",
            "organizations",
            "document_page_images",
            "document_payloads",
            "load_history",
        ):
            if _table_exists(conn, table) and _column_exists(conn, table, "document_id"):
                conn.execute(f"DELETE FROM {table} WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def _delete_related_ids(
    conn: sqlite3.Connection,
    target_table: str,
    target_column: str,
    source_table: str,
    source_column: str,
    document_id: str,
) -> None:
    if not _table_exists(conn, target_table) or not _table_exists(conn, source_table):
        return
    conn.execute(
        f"DELETE FROM {target_table} WHERE {target_column} IN "
        f"(SELECT {source_column} FROM {source_table} WHERE document_id = ?)",
        (document_id,),
    )


def _remove_from_fts(conn: sqlite3.Connection, document_id: str) -> None:
    if not _table_exists(conn, "documents_fts_content"):
        return
    row = conn.execute("SELECT rowid FROM documents_fts_content WHERE document_id = ?", (document_id,)).fetchone()
    if row is None:
        return
    rowid = row["rowid"]
    old = conn.execute(
        "SELECT content_free_text, fields_text, tags_text, people_text, orgs_text "
        "FROM documents_fts_content WHERE rowid = ?",
        (rowid,),
    ).fetchone()
    if old is not None and _table_exists(conn, "documents_fts"):
        conn.execute(
            "INSERT INTO documents_fts(documents_fts, rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) "
            "VALUES('delete', ?, ?, ?, ?, ?, ?)",
            (
                rowid,
                old["content_free_text"],
                old["fields_text"],
                old["tags_text"],
                old["people_text"],
                old["orgs_text"],
            ),
        )
    conn.execute("DELETE FROM documents_fts_content WHERE rowid = ?", (rowid,))


def _count_documents(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0").fetchone()[0]
    )


def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(conn, table_name):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] or "") == column_name for row in rows)
