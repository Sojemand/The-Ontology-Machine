from __future__ import annotations

import sqlite3
from typing import Any, Mapping, Sequence


def insert_row(
    conn: sqlite3.Connection,
    table: str,
    row: sqlite3.Row,
    *,
    skip_columns: Sequence[str] = (),
    overrides: Mapping[str, Any] | None = None,
) -> sqlite3.Cursor:
    table_columns = set(table_columns_for(conn, table))
    overrides = dict(overrides or {})
    skip = set(skip_columns)
    columns = [column for column in row.keys() if column in table_columns and column not in skip]
    values = [overrides.get(column, row[column]) for column in columns]
    extra_columns = [column for column in overrides if column in table_columns and column not in columns]
    columns.extend(extra_columns)
    values.extend(overrides[column] for column in extra_columns)
    placeholders = ", ".join("?" for _ in columns)
    return conn.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values)


def optional_int_map(mapping: Mapping[int, int], value: object) -> int | None:
    if value is None:
        return None
    return mapping.get(int(value))


def count_active_documents(conn: sqlite3.Connection) -> int:
    if not table_exists(conn, "documents"):
        return 0
    return int(conn.execute("SELECT COUNT(*) FROM documents WHERE COALESCE(is_archived, 0) = 0").fetchone()[0])


def count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    if not table_exists(conn, table_name):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns_for(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
