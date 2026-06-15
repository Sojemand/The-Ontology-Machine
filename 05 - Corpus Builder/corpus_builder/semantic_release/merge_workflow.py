"""Path-stable surface for snapshot-first corpus merges."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..database import connect
from ..models.serialization import now_iso
from .merge_confirmation import validate_collision_resolution, validate_snapshot_risk_confirmation
from .merge_constants import (
    COLLISION_ARCHIVE_EXISTING,
    COLLISION_OVERWRITE_EXISTING,
    SNAPSHOT_OVERRIDE_INTEGRITY_STATUS,
    SNAPSHOT_RISK_WARNING,
)
from .merge_documents import merge_documents
from .merge_preflight import build_merge_preflight, build_merge_preflight_from_connections, open_merge_connection
from .merge_snapshots import copy_global_audits, copy_materialization_runs, copy_semantic_snapshots
from .repository import collect_semantic_status
from .snapshots import sync_materialization_state_mirrors


def merge_corpus_databases(
    *,
    source_db_path: str | Path,
    target_db_path: str | Path,
    snapshot_risk_confirmation_artifact_path: str | Path | None = None,
    collision_resolution_artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    source_path = Path(source_db_path)
    target_path = Path(target_db_path)
    if source_path == target_path:
        raise ValueError("source_db_path und target_db_path muessen verschieden sein.")
    source_conn = open_merge_connection(source_path, label="source")
    target_conn = open_merge_connection(target_path, label="target")
    try:
        preflight = build_merge_preflight_from_connections(
            source_conn,
            target_conn,
            source_path=source_path,
            target_path=target_path,
        )
        if bool(preflight.get("blocked")):
            raise ValueError(str(preflight.get("blocked_reason") or "Merge ist blockiert."))
        snapshot_decision = validate_snapshot_risk_confirmation(
            artifact_path=snapshot_risk_confirmation_artifact_path,
            preflight=preflight,
        )
        collision_decision = validate_collision_resolution(
            artifact_path=collision_resolution_artifact_path,
            preflight=preflight,
        )
        counts = _merge_inside_transaction(
            source_conn,
            target_conn,
            preflight=preflight,
            source_path=source_path,
            target_path=target_path,
            snapshot_decision=snapshot_decision,
            collision_decision=collision_decision,
        )
    finally:
        source_conn.close()
        target_conn.close()
    target_status = _read_status_after_merge(target_path)
    return {
        "status": "merged",
        "source_db_path": str(source_path),
        "target_db_path": str(target_path),
        "master_taxonomy_release_id": preflight.get("master_taxonomy_release_id"),
        "active_snapshot_id": target_status.get("active_snapshot_id") if isinstance(target_status, dict) else None,
        "stale_documents": int((target_status or {}).get("stale_documents") or 0),
        "integrity_status": str((target_status or {}).get("integrity_status") or ""),
        "snapshot_risk_override_confirmed": snapshot_decision == "merge_anyway",
        "collision_resolution": collision_decision or None,
        **counts,
    }


def _merge_inside_transaction(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    preflight: dict[str, Any],
    source_path: Path,
    target_path: Path,
    snapshot_decision: str,
    collision_decision: str,
) -> dict[str, int]:
    try:
        target_conn.execute("BEGIN IMMEDIATE")
        target_conn.execute("PRAGMA defer_foreign_keys = ON")
        target_state = dict(preflight["target"])
        imported_snapshots = copy_semantic_snapshots(
            source_conn,
            target_conn,
            allow_invalid_source_snapshots=snapshot_decision == "merge_anyway",
        )
        imported_runs = copy_materialization_runs(source_conn, target_conn)
        imported_audits = copy_global_audits(source_conn, target_conn)
        merge_counts = merge_documents(source_conn, target_conn, collision_decision=collision_decision)
        if snapshot_decision == "merge_anyway":
            _record_snapshot_override(target_conn, preflight, source_path, target_path)
        _insert_audit(
            target_conn,
            level="info",
            code="corpus_merge_completed",
            message="Corpus merge completed.",
            details={
                "source_db_path": str(source_path),
                "target_db_path": str(target_path),
                "master_taxonomy_release_id": preflight.get("master_taxonomy_release_id"),
                "collision_decision": collision_decision or None,
                "snapshot_risk_override": snapshot_decision == "merge_anyway",
                **merge_counts,
            },
        )
        target_snapshot_id = str(target_state.get("active_snapshot_id") or "").strip()
        if target_snapshot_id:
            sync_materialization_state_mirrors(target_conn, target_snapshot_id)
        target_conn.commit()
        return {
            "imported_snapshot_count": imported_snapshots,
            "imported_materialization_run_count": imported_runs,
            "imported_global_audit_count": imported_audits,
            **merge_counts,
        }
    except Exception:
        if target_conn.in_transaction:
            target_conn.rollback()
        raise


def _record_snapshot_override(target_conn: sqlite3.Connection, preflight: dict[str, Any], source_path: Path, target_path: Path) -> None:
    source_state = dict(preflight["source"])
    target_state = dict(preflight["target"])
    _set_integrity_status(target_conn, SNAPSHOT_OVERRIDE_INTEGRITY_STATUS)
    _insert_audit(
        target_conn,
        level="warning",
        code="snapshot_override_confirmed",
        message=SNAPSHOT_RISK_WARNING,
        details={
            "source_db_path": str(source_path),
            "target_db_path": str(target_path),
            "master_taxonomy_release_id": preflight.get("master_taxonomy_release_id"),
            "source_snapshot_status": source_state.get("snapshot_status"),
            "target_snapshot_status": target_state.get("snapshot_status"),
        },
    )


def _insert_audit(conn: sqlite3.Connection, *, level: str, code: str, message: str, details: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO materialization_audit (created_at, level, code, document_id, projection_id, message, details_json) "
        "VALUES (?, ?, ?, NULL, NULL, ?, ?)",
        (now_iso(), level, code, message, json.dumps(details, ensure_ascii=False, sort_keys=True)),
    )


def _set_integrity_status(conn: sqlite3.Connection, integrity_status: str) -> None:
    conn.execute(
        "UPDATE installation_state SET integrity_status = ?, updated_at = CURRENT_TIMESTAMP WHERE singleton = 1",
        (integrity_status,),
    )


def _read_status_after_merge(target_path: Path) -> dict[str, Any]:
    conn = connect(str(target_path))
    try:
        return collect_semantic_status(conn)
    finally:
        conn.close()


__all__ = [
    "COLLISION_ARCHIVE_EXISTING",
    "COLLISION_OVERWRITE_EXISTING",
    "SNAPSHOT_OVERRIDE_INTEGRITY_STATUS",
    "SNAPSHOT_RISK_WARNING",
    "build_merge_preflight",
    "merge_corpus_databases",
    "validate_collision_resolution",
    "validate_snapshot_risk_confirmation",
]
