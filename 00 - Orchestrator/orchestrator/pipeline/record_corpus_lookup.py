from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..models import DocumentRecord
from . import debug, storage_repository, validation


def record_exists_in_selected_corpus(engine: Any, record: DocumentRecord, ui_state) -> bool:
    content_hash = str(record.content_hash or "").strip()
    if not content_hash:
        return False
    corpus_db_path = storage_repository.corpus_db_path(ui_state)
    if not corpus_db_path.exists() or not corpus_db_path.is_file():
        return False
    last_error: sqlite3.DatabaseError | None = None
    for target, uri in _corpus_connection_targets(corpus_db_path):
        try:
            conn = sqlite3.connect(target, uri=uri)
            try:
                return _corpus_contains_hash(conn, content_hash)
            finally:
                conn.close()
        except sqlite3.DatabaseError as exc:
            last_error = exc
    if last_error is not None:
        debug.append_log(engine, f"[DB-CHECK] Could not check selected DB: {corpus_db_path} -> {last_error}")
    return False


def _corpus_contains_hash(conn: sqlite3.Connection, content_hash: str) -> bool:
    columns = _table_columns(conn, "documents")
    if "content_hash" not in columns:
        return False
    archived_clause = "AND COALESCE(is_archived, 0) = 0" if "is_archived" in columns else ""
    row = conn.execute(
        f"SELECT 1 FROM documents WHERE content_hash = ? {archived_clause} LIMIT 1",
        (content_hash,),
    ).fetchone()
    return row is not None


def _corpus_connection_targets(corpus_db_path: Path) -> list[tuple[str, bool]]:
    targets = [(str(corpus_db_path), False)]
    try:
        db_uri = validation.resolved_path(corpus_db_path).as_uri()
        targets.append((db_uri + "?mode=ro", True))
        targets.append((db_uri + "?mode=ro&immutable=1", True))
    except ValueError:
        pass
    return targets


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}
