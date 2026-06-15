"""Backfill source identity columns for legacy-compatible corpus rows."""

from __future__ import annotations

import sqlite3

from ..models.source_identity import parse_source_identity
from .schema_introspection import existing_table_names


def backfill_source_identity(conn: sqlite3.Connection) -> None:
    if "documents" not in existing_table_names(conn):
        return
    rows = conn.execute(
        "SELECT id, file_path, content_hash, source_file_path, source_page, source_page_count "
        "FROM documents "
        "WHERE source_file_path IS NULL OR source_file_path = '' "
        "OR source_document_id IS NULL OR source_document_id = '' "
        "OR source_uri IS NULL OR source_uri = '' "
        "OR source_artifact_id IS NULL OR source_artifact_id = '' "
        "OR page_content_hash IS NULL OR page_content_hash = '' "
        "OR source_content_hash IS NULL OR source_content_hash = ''"
    ).fetchall()
    for row in rows:
        identity = parse_source_identity(str(row["file_path"] or ""))
        source_file_path = str(row["source_file_path"] or identity.source_file_path or row["file_path"] or "")
        source_page = row["source_page"] if row["source_page"] is not None else identity.source_page
        source_page_count = (
            row["source_page_count"] if row["source_page_count"] is not None else identity.source_page_count
        )
        page_index = max(0, int(source_page) - 1) if source_page is not None else 0
        source_document_id = source_file_path or str(row["file_path"] or row["id"])
        content_hash = str(row["content_hash"] or "")
        conn.execute(
            "UPDATE documents SET source_file_path = ?, source_page = ?, source_page_count = ?, "
            "source_document_id = COALESCE(NULLIF(source_document_id, ''), ?), "
            "source_uri = COALESCE(NULLIF(source_uri, ''), ?), "
            "source_artifact_id = COALESCE(NULLIF(source_artifact_id, ''), ?), "
            "ingest_run_id = COALESCE(NULLIF(ingest_run_id, ''), 'default'), "
            "page_index = CASE WHEN page_index IS NULL OR (page_index = 0 AND ? != 0) THEN ? ELSE page_index END, "
            "page_label = COALESCE(page_label, ?), "
            "materialization_order = CASE WHEN materialization_order IS NULL OR (materialization_order = 0 AND ? != 0) THEN ? ELSE materialization_order END, "
            "page_content_hash = COALESCE(NULLIF(page_content_hash, ''), ?), "
            "source_content_hash = COALESCE(NULLIF(source_content_hash, ''), ?) "
            "WHERE id = ?",
            (
                source_file_path,
                source_page,
                source_page_count,
                source_document_id,
                source_file_path,
                source_file_path,
                page_index,
                page_index,
                str(source_page) if source_page is not None else None,
                page_index,
                page_index,
                content_hash,
                content_hash,
                row["id"],
            ),
        )
