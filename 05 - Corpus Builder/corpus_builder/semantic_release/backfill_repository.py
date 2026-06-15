"""Repository helpers for semantic materialization backfill."""

from __future__ import annotations

import sqlite3
from typing import Any

from .sql_parameter_batches import iter_parameter_batches


def select_backfill_document_ids(
    conn: sqlite3.Connection,
    *,
    document_ids: list[str] | None = None,
    stale_only: bool = True,
    limit: int | None = None,
) -> list[str]:
    if document_ids:
        return _select_explicit_document_ids(conn, document_ids, limit=limit)

    where: list[str] = ["d.is_archived = 0"]
    params: list[Any] = []
    if stale_only:
        active_snapshot_id = _active_snapshot_id(conn)
        if active_snapshot_id:
            where.append("COALESCE(dps.materialized_snapshot_id, '') != ?")
            params.append(active_snapshot_id)
        else:
            where.append("COALESCE(dps.materialization_state, 'legacy') != 'current'")

    join = (
        " LEFT JOIN document_processing_state dps ON dps.document_id = d.id"
        if stale_only and not document_ids
        else ""
    )
    sql = f"SELECT d.id FROM documents d{join} WHERE {' AND '.join(where)} ORDER BY d.loaded_at DESC"
    if limit is not None and limit > 0:
        sql += f" LIMIT {int(limit)}"
    return [row["id"] for row in conn.execute(sql, params).fetchall()]


def _select_explicit_document_ids(
    conn: sqlite3.Connection,
    document_ids: list[str],
    *,
    limit: int | None,
) -> list[str]:
    rows: list[sqlite3.Row] = []
    for batch in iter_parameter_batches(document_ids):
        placeholders = ", ".join("?" for _ in batch)
        rows.extend(
            conn.execute(
                f"SELECT d.id, d.loaded_at FROM documents d WHERE d.is_archived = 0 AND d.id IN ({placeholders})",
                batch,
            ).fetchall()
        )
    rows.sort(key=lambda row: str(row["loaded_at"] or ""), reverse=True)
    ids = [str(row["id"]) for row in rows]
    return ids[:limit] if limit is not None and limit > 0 else ids


def create_materialization_run(
    conn: sqlite3.Connection,
    *,
    action: str,
    release_version: str,
    scope: str,
    notes: str,
) -> int:
    cursor = conn.execute(
        "INSERT INTO materialization_runs "
        "(action, release_version, scope, processed_count, stale_count, error_count, notes, started_at) "
        "VALUES (?, ?, ?, 0, 0, 0, ?, CURRENT_TIMESTAMP)",
        (action, release_version, scope, notes),
    )
    return int(cursor.lastrowid or 0)


def complete_materialization_run(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    processed_count: int,
    stale_count: int,
    error_count: int,
) -> None:
    conn.execute(
        "UPDATE materialization_runs SET processed_count = ?, stale_count = ?, "
        "error_count = ?, finished_at = CURRENT_TIMESTAMP WHERE run_id = ?",
        (processed_count, stale_count, error_count, run_id),
    )


def _active_snapshot_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT active_snapshot_id FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone()
    return str(row["active_snapshot_id"] or "").strip() if row is not None else ""
