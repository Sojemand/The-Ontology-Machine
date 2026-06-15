"""Repository reads for semantic release compatibility and status."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .backfill_repository import (
    complete_materialization_run,
    create_materialization_run,
    select_backfill_document_ids,
)
from .types import CompatibilityReport, SemanticStatusReport


def inspect_release_application_compatibility(
    conn: sqlite3.Connection,
    release: dict[str, Any],
) -> CompatibilityReport:
    release_projection_ids = {
        str(value).strip()
        for value in release.get("projection_ids", []) or []
        if str(value).strip()
    }
    release_master_id = str(release.get("master_taxonomy_id") or "").strip()
    strict_master_line = _has_active_release_fingerprint(conn)
    missing_projection_ids: list[str] = []
    incompatible_projection_ids: list[str] = []
    foreign_master_ids: list[str] = []
    rows = conn.execute(
        "SELECT d.id, dps.projection_id, dp.projection_json "
        "FROM documents d "
        "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
        "JOIN document_payloads dp ON dp.document_id = d.id "
        "WHERE d.is_archived = 0"
    ).fetchall()
    for row in rows:
        document_id = str(row["id"] or "").strip()
        projection_id = str(row["projection_id"] or "").strip()
        if not projection_id:
            missing_projection_ids.append(document_id)
            continue
        if projection_id not in release_projection_ids:
            incompatible_projection_ids.append(document_id)
            continue
        projection_json = _load_projection_json(row["projection_json"])
        input_master_id = str((projection_json or {}).get("master_taxonomy_id") or "").strip()
        if strict_master_line and input_master_id and release_master_id and input_master_id != release_master_id:
            foreign_master_ids.append(document_id)
    return {
        "missing_projection_ids": missing_projection_ids,
        "incompatible_projection_ids": incompatible_projection_ids,
        "foreign_master_ids": foreign_master_ids,
    }


def collect_semantic_status(conn: sqlite3.Connection) -> SemanticStatusReport:
    total_documents = conn.execute("SELECT COUNT(*) FROM documents WHERE is_archived = 0").fetchone()[0]
    installation_state = conn.execute(
        "SELECT active_snapshot_id, active_release_id, active_release_version, active_release_fingerprint, "
        "master_taxonomy_release_id, runtime_locale, integrity_status, materialization_version "
        "FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone()
    active_snapshot_id = (
        str(installation_state["active_snapshot_id"] or "").strip()
        if installation_state is not None and "active_snapshot_id" in installation_state.keys()
        else ""
    )
    if active_snapshot_id:
        stale_documents = conn.execute(
            "SELECT COUNT(*) "
            "FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE d.is_archived = 0 AND COALESCE(dps.materialized_snapshot_id, '') != ?",
            (active_snapshot_id,),
        ).fetchone()[0]
        runtime_truth_source = "db_snapshot"
    else:
        stale_documents = conn.execute(
            "SELECT COUNT(*) "
            "FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE d.is_archived = 0 AND COALESCE(dps.materialization_state, 'legacy') != 'current'"
        ).fetchone()[0]
        runtime_truth_source = "snapshot_missing" if installation_state and str(installation_state["active_release_fingerprint"] or "").strip() else "uninitialized"
    return {
        "total_documents": total_documents,
        "stale_documents": stale_documents,
        "active_snapshot_id": active_snapshot_id or None,
        "active_release_id": installation_state["active_release_id"] if installation_state else None,
        "active_release_version": installation_state["active_release_version"] if installation_state else None,
        "active_release_fingerprint": installation_state["active_release_fingerprint"] if installation_state else None,
        "active_master_taxonomy_release_id": installation_state["master_taxonomy_release_id"] if installation_state else None,
        "active_runtime_locale": installation_state["runtime_locale"] if installation_state else None,
        "integrity_status": installation_state["integrity_status"] if installation_state else None,
        "materialization_version": installation_state["materialization_version"] if installation_state else None,
        "runtime_truth_source": runtime_truth_source,
    }


def count_unknown_projection_documents(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) "
            "FROM documents d "
            "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
            "WHERE COALESCE(dps.projection_id, '') = ''"
        ).fetchone()[0]
    )


def apply_release_installation_state(conn: sqlite3.Connection, snapshot: dict[str, Any]) -> None:
    release = dict(snapshot.get("release") or {})
    active_snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    runtime_locale = snapshot.get("runtime_locale")
    conn.execute(
        "UPDATE installation_state SET "
        "active_snapshot_id = ?, active_release_id = ?, active_release_version = ?, active_release_fingerprint = ?, "
        "master_taxonomy_id = ?, master_taxonomy_version = ?, master_taxonomy_release_id = ?, runtime_locale = ?, "
        "materialization_version = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE singleton = 1",
        (
            active_snapshot_id,
            release.get("release_id"),
            release.get("release_version"),
            release.get("fingerprint"),
            release.get("master_taxonomy_id"),
            release.get("master_taxonomy_version"),
            release.get("master_taxonomy_release_id"),
            runtime_locale,
            release.get("materialization_version"),
        ),
    )


def _has_active_release_fingerprint(conn: sqlite3.Connection) -> bool:
    if not _table_exists(conn, "installation_state"):
        return False
    row = conn.execute(
        "SELECT active_release_fingerprint FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone()
    return row is not None and bool(str(row["active_release_fingerprint"] or "").strip())


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _load_projection_json(raw_value: str | None) -> dict[str, Any] | None:
    if not raw_value:
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
