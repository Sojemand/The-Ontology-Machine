"""Repository stage for search-related SQLite reads."""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Sequence

from . import policy
from .types import PreparedSqlStatement, SearchFilter

logger = logging.getLogger(__name__)

_LIMIT_PATTERN = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_FTS_BASE_SQL = """
    SELECT d.id,
           COALESCE(
               (SELECT p.display_value FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1 AND p.query_role = 'title' ORDER BY p.ordinal, p.promotion_id LIMIT 1),
               (SELECT p.display_value FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1 ORDER BY p.ordinal, p.promotion_id LIMIT 1),
               d.file_name
           ) AS result_title,
           COALESCE(
               (SELECT GROUP_CONCAT(p.slot || ': ' || p.display_value, ' | ') FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1),
               NULLIF(d.content_free_text, '')
           ) AS result_description,
           rank AS fts_rank,
           snippet(documents_fts, -1, '<b>', '</b>', '...', 32) AS snippet
    FROM documents_fts fts
    JOIN documents_fts_content fc ON fts.rowid = fc.rowid
    JOIN documents d ON fc.document_id = d.id
    WHERE documents_fts MATCH ?
      AND d.is_archived = 0
"""


def has_embeddings(conn: sqlite3.Connection) -> bool:
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name IN ('embeddings', 'embedding_chunks')"
        ).fetchall()
    }
    if "embedding_chunks" in tables:
        row = conn.execute(
            "SELECT CASE "
            "WHEN EXISTS(SELECT 1 FROM embeddings LIMIT 1) THEN 1 "
            "WHEN EXISTS(SELECT 1 FROM embedding_chunks LIMIT 1) THEN 1 "
            "ELSE 0 END"
        ).fetchone()
        return bool(row and row[0] > 0)
    row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
    return bool(row and row[0] > 0)


def search_fulltext_rows(
    conn: sqlite3.Connection,
    query: str,
    filters: list[SearchFilter],
    *,
    limit: int,
) -> list[sqlite3.Row]:
    sql = _FTS_BASE_SQL
    params: list[object] = [query]

    for filter_item in filters:
        if filter_item.key == "entity_type":
            sql += (
                " AND EXISTS (SELECT 1 FROM document_entities de "
                "WHERE de.document_id = d.id AND de.entity_type = ?)"
            )
        elif filter_item.key == "promotion_slot":
            sql += " AND EXISTS (SELECT 1 FROM document_promotions p WHERE p.document_id = d.id AND p.is_current = 1 AND p.slot = ?)"
        elif filter_item.key == "promotion_value":
            sql = _append_promotion_value_filter(sql, params, slot=None, value=filter_item.value)
            continue
        elif filter_item.key.startswith("promotion:") or filter_item.key.startswith("slot:"):
            slot = filter_item.key.split(":", 1)[1].strip()
            if not slot:
                continue
            sql = _append_promotion_value_filter(sql, params, slot=slot, value=filter_item.value)
            continue
        elif filter_item.key == "role_type":
            sql += (
                " AND EXISTS (SELECT 1 FROM document_entities de "
                "WHERE de.document_id = d.id AND de.role_type = ?)"
            )
        elif filter_item.key == "materialization_state":
            sql += (
                " AND EXISTS (SELECT 1 FROM document_processing_state dps "
                "WHERE dps.document_id = d.id AND dps.materialization_state = ?)"
            )
        elif policy.filter_operator(filter_item.value) == "like":
            sql += f" AND d.{filter_item.key} LIKE ?"
        else:
            sql += f" AND d.{filter_item.key} = ?"
        params.append(filter_item.value)

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def _append_promotion_value_filter(
    sql: str,
    params: list[object],
    *,
    slot: str | None,
    value: object,
) -> str:
    if policy.filter_operator(value) == "like":
        operator = "LIKE"
        value_param = value
    else:
        operator = "="
        value_param = str(value)
    slot_clause = "AND p.slot = ? " if slot else ""
    sql += (
        " AND EXISTS (SELECT 1 FROM document_promotions p "
        f"WHERE p.document_id = d.id AND p.is_current = 1 {slot_clause}"
        f"AND (p.display_value {operator} ? OR p.normalized_value {operator} ? OR p.compact_value {operator} ?))"
    )
    if slot:
        params.append(slot)
    params.extend([value_param, value_param, value_param])
    return sql


def execute_readonly_query(
    conn: sqlite3.Connection,
    prepared: PreparedSqlStatement,
    params: Sequence[object] | None,
    *,
    max_rows: int,
) -> list[dict]:
    execute_sql = prepared.statement[:-1].rstrip() if prepared.has_trailing_semicolon else prepared.statement
    if not _LIMIT_PATTERN.search(prepared.masked_statement):
        execute_sql = f"{execute_sql} LIMIT {max_rows}"

    try:
        cursor = conn.execute(execute_sql, tuple(params or ()))
        rows = cursor.fetchmany(max_rows)
    except sqlite3.OperationalError as exc:
        logger.error("safe_query fehlgeschlagen: %s - SQL: %s", exc, execute_sql[:200])
        raise
    return [dict(row) for row in rows]
