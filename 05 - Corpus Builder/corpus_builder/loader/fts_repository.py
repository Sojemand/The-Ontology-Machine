"""FTS persistence helpers for loader repository."""

from __future__ import annotations

import sqlite3

from ..models.serialization import now_iso
from .policy import is_non_empty
from .search_text import build_fallback_search_text, build_fts_fields_text
from .types import JsonDict


def remove_from_fts(conn: sqlite3.Connection, doc_id: str) -> None:
    row = conn.execute("SELECT rowid FROM documents_fts_content WHERE document_id = ?", (doc_id,)).fetchone()
    if not row:
        return
    rowid = row["rowid"]
    old = conn.execute("SELECT content_free_text, fields_text, tags_text, people_text, orgs_text FROM documents_fts_content WHERE rowid = ?", (rowid,)).fetchone()
    if old:
        conn.execute(
            "INSERT INTO documents_fts(documents_fts, rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES('delete', ?, ?, ?, ?, ?, ?)",
            (rowid, old["content_free_text"], old["fields_text"], old["tags_text"], old["people_text"], old["orgs_text"]),
        )
    conn.execute("DELETE FROM documents_fts_content WHERE rowid = ?", (rowid,))


def archive_document(conn: sqlite3.Connection, doc_id: str) -> None:
    conn.execute("UPDATE documents SET is_archived = 1, archived_at = ? WHERE id = ?", (now_iso(), doc_id))
    remove_from_fts(conn, doc_id)


def insert_fts_entry(
    conn: sqlite3.Connection,
    doc_id: str,
    doc: JsonDict,
    fields: JsonDict,
    rows: list[JsonDict],
    segments: list[JsonDict],
    tags: list[str],
    people: list[str],
    orgs: list[str],
    promotions: list[JsonDict] | None = None,
) -> None:
    free_text = doc.get("content_free_text")
    search_text = str(free_text).strip() if is_non_empty(free_text) else build_fallback_search_text(doc, fields, rows, segments, tags, people, orgs, promotions)
    fields_text = build_fts_fields_text(doc, fields, rows, segments, promotions)
    cursor = conn.execute(
        "INSERT INTO documents_fts_content (document_id, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, search_text or None, fields_text, " ".join(tags), " ".join(people), " ".join(orgs)),
    )
    conn.execute(
        "INSERT INTO documents_fts(rowid, content_free_text, fields_text, tags_text, people_text, orgs_text) VALUES (?, ?, ?, ?, ?, ?)",
        (cursor.lastrowid, search_text or None, fields_text, " ".join(tags), " ".join(people), " ".join(orgs)),
    )
