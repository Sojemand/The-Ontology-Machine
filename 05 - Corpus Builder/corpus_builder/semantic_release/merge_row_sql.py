from __future__ import annotations

import sqlite3
from typing import Any


def insert_dynamic_row(target_conn: sqlite3.Connection, table_name: str, payload: dict[str, Any]) -> int:
    columns = list(payload)
    placeholders = ", ".join("?" for _ in columns)
    values = [payload[column] for column in columns]
    cursor = target_conn.execute(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})", values)
    return int(cursor.lastrowid or 0)


def rewrite_document_targets(payload: dict[str, Any], rewrite_map: dict[str, str] | None) -> None:
    if not rewrite_map:
        return
    target_document_id = str(payload.get("target_document_id") or "").strip()
    if target_document_id and target_document_id in rewrite_map:
        payload["target_document_id"] = rewrite_map[target_document_id]
