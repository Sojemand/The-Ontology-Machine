from __future__ import annotations

from .tool_handler_deps import *


def create_workspace_release_package(
    *,
    normalizer_home: Path,
    language: str,
    projection_ids: list[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": "create_release_package", "default_runtime_locale": language}
    if projection_ids:
        payload["projection_ids"] = projection_ids
    return _invoke_edit(
        "normalizer",
        payload,
        env_overrides=_workspace_normalizer_env(normalizer_home),
    )


def read_release_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def inspect_workspace_db_for_revision(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return _db_state(False, "missing", 0)
    if not db_path.is_file():
        raise ToolFailure(f"corpus_db_path muss eine Datei sein: {db_path}")
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            tables = _sqlite_tables(conn)
            if "documents" not in tables:
                return _db_state(True, "sqlite_without_corpus_schema", 0)
            document_count = _count_active_documents(conn)
            return _db_state(
                True,
                "populated" if document_count else "empty",
                document_count,
                active_projection_ids=_distinct_text_values(conn, "document_processing_state", "projection_id"),
                active_master_taxonomy_release_ids=_distinct_text_values(
                    conn,
                    "document_processing_state",
                    "master_taxonomy_release_id",
                ),
            )
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ToolFailure(f"corpus_db_path ist keine lesbare SQLite-DB: {db_path}") from exc


def _db_state(
    exists: bool,
    state: str,
    document_count: int,
    *,
    active_projection_ids: list[str] | None = None,
    active_master_taxonomy_release_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "exists": exists,
        "state": state,
        "document_count": document_count,
        "active_projection_ids": active_projection_ids or [],
        "active_master_taxonomy_release_ids": active_master_taxonomy_release_ids or [],
    }


def _count_active_documents(conn: sqlite3.Connection) -> int:
    if "is_archived" in _table_columns(conn, "documents"):
        row = conn.execute("SELECT COUNT(*) FROM documents WHERE is_archived = 0").fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    return int(row[0] if row else 0)


def _distinct_text_values(conn: sqlite3.Connection, table: str, column: str) -> list[str]:
    if table not in _sqlite_tables(conn) or column not in _table_columns(conn, table):
        return []
    rows = conn.execute(
        f"SELECT DISTINCT {column} FROM {table} WHERE COALESCE({column}, '') != '' ORDER BY {column}"
    ).fetchall()
    return [str(row[0]).strip() for row in rows if str(row[0] or "").strip()]


def _sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


__all__ = [name for name in globals() if not name.startswith("__")]
