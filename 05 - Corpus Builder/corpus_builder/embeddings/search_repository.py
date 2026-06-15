"""Embedding search candidate read models."""

from __future__ import annotations

import sqlite3

from .types import SearchCandidate

_RESULT_TITLE_SQL = (
    "COALESCE((SELECT p.display_value FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1 AND p.query_role = 'title' ORDER BY p.ordinal, p.promotion_id LIMIT 1), "
    "(SELECT p.display_value FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1 ORDER BY p.ordinal, p.promotion_id LIMIT 1), "
    "d.file_name)"
)
_RESULT_DESCRIPTION_SQL = (
    "COALESCE((SELECT GROUP_CONCAT(p.slot || ': ' || p.display_value, ' | ') FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1), "
    "NULLIF(d.content_free_text, ''))"
)


def fetch_chunk_search_candidates(conn: sqlite3.Connection) -> list[SearchCandidate]:
    if not _table_exists(conn, "embedding_chunks"):
        return []
    rows = conn.execute(
        "SELECT ec.document_id, ec.chunk_text, ec.vector, ec.dimensions, ec.page, ec.chunk_type, "
        f"{_RESULT_TITLE_SQL} AS result_title, {_RESULT_DESCRIPTION_SQL} AS result_description "
        "FROM embedding_chunks ec "
        "JOIN documents d ON ec.document_id = d.id "
        "WHERE d.is_archived = 0 "
        "ORDER BY ec.document_id, ec.chunk_index"
    ).fetchall()
    return [
        SearchCandidate(
            document_id=str(row["document_id"]),
            title=row["result_title"],
            description=row["result_description"],
            vector_blob=bytes(row["vector"]),
            dimensions=int(row["dimensions"]),
            snippet=_chunk_snippet(
                str(row["chunk_text"] or ""),
                page=row["page"],
                chunk_type=row["chunk_type"],
            ),
        )
        for row in rows
    ]


def fetch_document_search_candidates(conn: sqlite3.Connection) -> list[SearchCandidate]:
    rows = conn.execute(
        f"SELECT e.document_id, e.vector, e.dimensions, {_RESULT_TITLE_SQL} AS result_title, {_RESULT_DESCRIPTION_SQL} AS result_description "
        "FROM embeddings e JOIN documents d ON e.document_id = d.id "
        "WHERE d.is_archived = 0"
    ).fetchall()
    return [
        SearchCandidate(
            document_id=str(row["document_id"]),
            title=row["result_title"],
            description=row["result_description"],
            vector_blob=bytes(row["vector"]),
            dimensions=int(row["dimensions"]),
        )
        for row in rows
    ]


def fetch_search_candidates(conn: sqlite3.Connection) -> list[SearchCandidate]:
    return fetch_document_search_candidates(conn)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _chunk_snippet(text: str, *, page: object, chunk_type: object) -> str | None:
    collapsed = " ".join(text.split()).strip()
    if not collapsed:
        return None
    prefix_parts: list[str] = []
    if page is not None:
        prefix_parts.append(f"Seite {page}")
    if chunk_type:
        prefix_parts.append(str(chunk_type))
    prefix = f"{' | '.join(prefix_parts)}: " if prefix_parts else ""
    body = collapsed[:197].rstrip() + "..." if len(collapsed) > 200 else collapsed
    return prefix + body
