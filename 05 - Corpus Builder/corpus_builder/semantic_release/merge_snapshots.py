"""Snapshot and run copy helpers for corpus merges."""

from __future__ import annotations

import json
import sqlite3

from .snapshots import build_snapshot_id


def copy_semantic_snapshots(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    allow_invalid_source_snapshots: bool = False,
) -> int:
    imported = 0
    rows = source_conn.execute(
        "SELECT snapshot_id, release_json, master_taxonomy_release_id, runtime_locale, release_id, release_version, release_fingerprint, release_path, created_at "
        "FROM semantic_snapshots ORDER BY created_at, snapshot_id"
    ).fetchall()
    for row in rows:
        if allow_invalid_source_snapshots and not _snapshot_row_payload_valid(row):
            continue
        existing = target_conn.execute(
            "SELECT release_json, master_taxonomy_release_id, runtime_locale, release_id, release_version, release_fingerprint "
            "FROM semantic_snapshots WHERE snapshot_id = ?",
            (row["snapshot_id"],),
        ).fetchone()
        if existing is not None:
            if not _snapshot_rows_compatible(existing, row):
                raise ValueError(f"Snapshot-Kollision im Ziel gefunden: {row['snapshot_id']}")
            continue
        target_conn.execute(
            "INSERT INTO semantic_snapshots "
            "(snapshot_id, release_json, master_taxonomy_release_id, runtime_locale, release_id, release_version, release_fingerprint, release_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(row[key] for key in (
                "snapshot_id",
                "release_json",
                "master_taxonomy_release_id",
                "runtime_locale",
                "release_id",
                "release_version",
                "release_fingerprint",
                "release_path",
                "created_at",
            )),
        )
        imported += 1
    return imported


def copy_materialization_runs(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection) -> int:
    imported = 0
    rows = source_conn.execute(
        "SELECT action, release_version, scope, processed_count, stale_count, error_count, notes, started_at, finished_at "
        "FROM materialization_runs ORDER BY run_id"
    ).fetchall()
    for row in rows:
        target_conn.execute(
            "INSERT INTO materialization_runs "
            "(action, release_version, scope, processed_count, stale_count, error_count, notes, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(row[key] for key in (
                "action",
                "release_version",
                "scope",
                "processed_count",
                "stale_count",
                "error_count",
                "notes",
                "started_at",
                "finished_at",
            )),
        )
        imported += 1
    return imported


def copy_global_audits(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection) -> int:
    imported = 0
    rows = source_conn.execute(
        "SELECT created_at, level, code, message, details_json "
        "FROM materialization_audit WHERE document_id IS NULL ORDER BY audit_id"
    ).fetchall()
    for row in rows:
        target_conn.execute(
            "INSERT INTO materialization_audit (created_at, level, code, document_id, projection_id, message, details_json) "
            "VALUES (?, ?, ?, NULL, NULL, ?, ?)",
            (row["created_at"], row["level"], row["code"], row["message"], row["details_json"]),
        )
        imported += 1
    return imported


def _snapshot_rows_compatible(existing: sqlite3.Row, incoming: sqlite3.Row) -> bool:
    for key in ("master_taxonomy_release_id", "runtime_locale", "release_id", "release_version", "release_fingerprint"):
        if existing[key] != incoming[key]:
            return False
    return _snapshot_json_equivalent(existing["release_json"], incoming["release_json"])


def _snapshot_row_payload_valid(row: sqlite3.Row) -> bool:
    raw_value = str(row["release_json"] or "").strip()
    if not raw_value:
        return False
    try:
        release = json.loads(raw_value)
    except json.JSONDecodeError:
        return False
    if not isinstance(release, dict):
        return False
    try:
        return build_snapshot_id(release) == str(row["snapshot_id"] or "").strip()
    except Exception:
        return False


def _snapshot_json_equivalent(left: str | None, right: str | None) -> bool:
    if left == right:
        return True
    try:
        left_payload = json.loads(str(left or ""))
        right_payload = json.loads(str(right or ""))
    except json.JSONDecodeError:
        return False
    if not isinstance(left_payload, dict) or not isinstance(right_payload, dict):
        return False
    try:
        return build_snapshot_id(left_payload) == build_snapshot_id(right_payload)
    except Exception:
        return False


__all__ = ["copy_global_audits", "copy_materialization_runs", "copy_semantic_snapshots"]
