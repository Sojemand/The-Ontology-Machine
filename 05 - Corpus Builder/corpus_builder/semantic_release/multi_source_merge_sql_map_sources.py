from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ..database import connect_readonly


def source_databases(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in selection.get("source_databases", []) if isinstance(item, Mapping)]


def source_document_rows(source_database_path: Path) -> list[sqlite3.Row]:
    if not source_database_path.exists():
        raise ValueError(f"source_database_missing: source database does not exist: {source_database_path}")
    conn = connect_readonly(str(source_database_path))
    try:
        if not table_exists(conn, "documents"):
            raise ValueError("source_database_invalid: source database does not contain documents.")
        return conn.execute(
            "SELECT * FROM documents WHERE COALESCE(is_archived, 0) = 0 ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def source_embedding_id(source_database_path: Path, document_id: str) -> str:
    conn = connect_readonly(str(source_database_path))
    try:
        if table_exists(conn, "embeddings"):
            row = conn.execute("SELECT document_id FROM embeddings WHERE document_id = ?", (document_id,)).fetchone()
            if row is not None:
                return str(row["document_id"])
        return ""
    finally:
        conn.close()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None
