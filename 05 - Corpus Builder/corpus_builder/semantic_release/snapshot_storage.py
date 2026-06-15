"""SQLite storage helpers for semantic release snapshots."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .snapshot_identity import build_snapshot_envelope, build_snapshot_id, release_without_active_snapshot
from .types import ActiveSnapshotEnvelope


def read_active_snapshot(conn: sqlite3.Connection) -> ActiveSnapshotEnvelope | None:
    if not _table_exists(conn, "semantic_snapshots") or not _column_exists(conn, "installation_state", "active_snapshot_id"):
        return None
    state = conn.execute(
        "SELECT active_snapshot_id FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone()
    active_snapshot_id = str(state["active_snapshot_id"] or "").strip() if state is not None else ""
    if not active_snapshot_id:
        return None
    row = conn.execute(
        "SELECT snapshot_id, release_json, release_path FROM semantic_snapshots WHERE snapshot_id = ?",
        (active_snapshot_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Aktiver Semantic Snapshot fehlt: {active_snapshot_id}")
    release = _load_release_json(row["release_json"])
    expected_snapshot_id = build_snapshot_id(release)
    if expected_snapshot_id != active_snapshot_id:
        raise ValueError(f"Semantic Snapshot ist inkonsistent: {active_snapshot_id} != {expected_snapshot_id}")
    return build_snapshot_envelope(
        release,
        release_path=str(row["release_path"] or ""),
        snapshot_id=active_snapshot_id,
    )


def write_snapshot(conn: sqlite3.Connection, release: dict[str, Any], *, release_path: str) -> ActiveSnapshotEnvelope:
    snapshot = build_snapshot_envelope(release, release_path=release_path)
    stored_release = release_without_active_snapshot(snapshot["release"])
    conn.execute(
        "INSERT OR IGNORE INTO semantic_snapshots "
        "(snapshot_id, release_json, master_taxonomy_release_id, runtime_locale, release_id, release_version, "
        "release_fingerprint, release_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            snapshot["snapshot_id"],
            json.dumps(stored_release, ensure_ascii=False),
            snapshot["master_taxonomy_release_id"],
            snapshot["runtime_locale"],
            snapshot["release"]["release_id"],
            snapshot["release"]["release_version"],
            snapshot["release"]["fingerprint"],
            snapshot["release_path"],
        ),
    )
    return snapshot


def count_stale_documents_for_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) "
            "FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE d.is_archived = 0 AND COALESCE(dps.materialized_snapshot_id, '') != ?",
            (snapshot_id,),
        ).fetchone()[0]
    )


def sync_materialization_state_mirrors(conn: sqlite3.Connection, active_snapshot_id: str | None) -> None:
    conn.execute(
        "UPDATE document_processing_state SET "
        "materialization_state = CASE "
        "WHEN ? IS NOT NULL AND ? != '' AND COALESCE(materialized_snapshot_id, '') = ? THEN 'current' "
        "WHEN ? IS NOT NULL AND ? != '' THEN 'stale' "
        "ELSE COALESCE(materialization_state, 'legacy') END, "
        "stale_reason = CASE "
        "WHEN ? IS NOT NULL AND ? != '' AND COALESCE(materialized_snapshot_id, '') = ? THEN NULL "
        "WHEN ? IS NOT NULL AND ? != '' THEN 'active_snapshot_changed' "
        "ELSE stale_reason END",
        (
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
            active_snapshot_id,
        ),
    )


def _load_release_json(raw_value: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError("semantic_snapshots.release_json ist ungueltig.") from exc
    if not isinstance(payload, dict):
        raise ValueError("semantic_snapshots.release_json muss ein JSON-Objekt sein.")
    return payload


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    if not _table_exists(conn, table_name):
        return False
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"] or "") == column_name for row in rows)
