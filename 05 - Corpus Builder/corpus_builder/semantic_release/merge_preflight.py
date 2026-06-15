"""Preflight inspection for snapshot-first corpus merges."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from ..database import connect, has_initialized_schema
from .merge_constants import ACTIVE_DOC_SQL
from .merge_preflight_helpers import (
    allow_with_stale_reasons,
    classify_snapshot_status,
    pending_interactions,
    row_dict,
)
from .repository import collect_semantic_status
from .snapshots import read_active_snapshot


def build_merge_preflight(*, source_db_path: str | Path, target_db_path: str | Path) -> dict[str, Any]:
    source_path = Path(source_db_path)
    target_path = Path(target_db_path)
    if source_path == target_path:
        raise ValueError("source_db_path und target_db_path muessen verschieden sein.")
    source_conn = open_merge_connection(source_path, label="source")
    target_conn = open_merge_connection(target_path, label="target")
    try:
        return build_merge_preflight_from_connections(
            source_conn,
            target_conn,
            source_path=source_path,
            target_path=target_path,
        )
    finally:
        source_conn.close()
        target_conn.close()


def build_merge_preflight_from_connections(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    source_path: Path,
    target_path: Path,
) -> dict[str, Any]:
    source_state = inspect_merge_db(source_conn, source_path)
    target_state = inspect_merge_db(target_conn, target_path)
    source_master = str(source_state.get("master_taxonomy_release_id") or "").strip()
    target_master = str(target_state.get("master_taxonomy_release_id") or "").strip()
    blocked_reason = blocked_merge_reason(source_state, target_state)
    collisions = sorted(source_state["document_ids"] & target_state["document_ids"])
    collision_fingerprint = collision_fingerprint_for(collisions)
    snapshot_risk = blocked_reason is None and (
        not bool(source_state.get("snapshot_ok")) or not bool(target_state.get("snapshot_ok"))
    )
    interactions = pending_interactions(
        snapshot_risk=snapshot_risk,
        collisions=collisions,
        collision_fingerprint=collision_fingerprint,
        source_path=source_path,
        target_path=target_path,
        source_master=source_master,
        source_state=source_state,
        target_state=target_state,
        collision_allowed=blocked_reason is None,
    )
    return {
        "source_db_path": str(source_path),
        "target_db_path": str(target_path),
        "master_taxonomy_release_id": source_master if source_master == target_master else None,
        "source": source_state,
        "target": target_state,
        "blocked": blocked_reason is not None,
        "blocked_reason": blocked_reason,
        "merge_ready": blocked_reason is None and not interactions,
        "snapshot_risk_confirmation_required": snapshot_risk,
        "collision_resolution_required": bool(collisions) and blocked_reason is None,
        "collision_count": len(collisions),
        "collision_document_ids": collisions[:25],
        "collision_fingerprint": collision_fingerprint,
        "allow_with_stale_reasons": allow_with_stale_reasons(source_state, target_state),
        "stale_documents_after_merge_estimate": stale_documents_after_merge_estimate(
            source_conn,
            target_active_snapshot_id=str(target_state.get("active_snapshot_id") or ""),
        ),
        "pending_interactions": interactions,
        "merge_payload_template": {
            "action": "merge_corpus_databases",
            "source_db_path": str(source_path),
            "target_db_path": str(target_path),
        },
    }


def open_merge_connection(path: Path, *, label: str) -> sqlite3.Connection:
    if not path.exists():
        raise ValueError(f"{label}_corpus_db_not_found: {path}")
    conn = connect(str(path))
    if not has_initialized_schema(conn):
        conn.close()
        raise ValueError(f"{label}_corpus_db_uninitialized: {path}")
    return conn


def inspect_merge_db(conn: sqlite3.Connection, path: Path) -> dict[str, Any]:
    installation = row_dict(conn.execute(
        "SELECT active_snapshot_id, master_taxonomy_release_id, runtime_locale, active_release_id, "
        "active_release_version, active_release_fingerprint, integrity_status "
        "FROM installation_state WHERE singleton = 1 LIMIT 1"
    ).fetchone())
    status = collect_semantic_status(conn)
    active_snapshot_id = str(installation.get("active_snapshot_id") or "").strip()
    master_taxonomy_release_id = str(installation.get("master_taxonomy_release_id") or "").strip()
    runtime_locale = str(installation.get("runtime_locale") or "").strip()
    snapshot, snapshot_reason = None, ""
    try:
        snapshot = read_active_snapshot(conn)
    except Exception as exc:
        snapshot_reason = str(exc)
    if snapshot is not None:
        master_taxonomy_release_id = str(snapshot.get("master_taxonomy_release_id") or "").strip()
        runtime_locale = str(snapshot.get("runtime_locale") or "").strip()
        active_snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    elif not master_taxonomy_release_id:
        lines = distinct_master_lines(conn)
        if len(lines) == 1:
            master_taxonomy_release_id = lines[0]
    return {
        "db_path": str(path),
        "active_snapshot_id": active_snapshot_id or None,
        "snapshot_ok": snapshot is not None,
        "snapshot_status": classify_snapshot_status(active_snapshot_id, snapshot, snapshot_reason),
        "snapshot_reason": snapshot_reason or None,
        "active_snapshot": snapshot,
        "master_taxonomy_release_id": master_taxonomy_release_id or None,
        "runtime_locale": runtime_locale or None,
        "active_release_id": str(installation.get("active_release_id") or "").strip() or None,
        "active_release_version": str(installation.get("active_release_version") or "").strip() or None,
        "active_release_fingerprint": str(installation.get("active_release_fingerprint") or "").strip() or None,
        "integrity_status": str(installation.get("integrity_status") or status.get("integrity_status") or "").strip() or None,
        "total_documents": int(status.get("total_documents") or 0),
        "stale_documents": int(status.get("stale_documents") or 0),
        "document_ids": document_ids(conn),
    }


def blocked_merge_reason(source_state: dict[str, Any], target_state: dict[str, Any]) -> str | None:
    source_master = str(source_state.get("master_taxonomy_release_id") or "").strip()
    target_master = str(target_state.get("master_taxonomy_release_id") or "").strip()
    if not source_master or not target_master:
        return "Merge blockiert: master_taxonomy_release_id ist nicht belastbar bestimmbar."
    if source_master != target_master:
        return "Merge blockiert: unterschiedliche master_taxonomy_release_id."
    return None


def stale_documents_after_merge_estimate(source_conn: sqlite3.Connection, *, target_active_snapshot_id: str) -> int:
    if not target_active_snapshot_id:
        return int(source_conn.execute(ACTIVE_DOC_SQL).fetchone()[0])
    return int(source_conn.execute(
        "SELECT COUNT(*) FROM documents d "
        "LEFT JOIN document_processing_state dps ON dps.document_id = d.id "
        "WHERE d.is_archived = 0 AND COALESCE(dps.materialized_snapshot_id, '') != ?",
        (target_active_snapshot_id,),
    ).fetchone()[0])


def document_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT id FROM documents").fetchall()
    return {str(row["id"]).strip() for row in rows if str(row["id"]).strip()}


def distinct_master_lines(conn: sqlite3.Connection) -> list[str]:
    if not table_exists(conn, "semantic_snapshots"):
        return []
    rows = conn.execute(
        "SELECT DISTINCT master_taxonomy_release_id FROM semantic_snapshots "
        "WHERE master_taxonomy_release_id IS NOT NULL AND master_taxonomy_release_id != ''"
    ).fetchall()
    return sorted(str(row["master_taxonomy_release_id"]).strip() for row in rows if str(row["master_taxonomy_release_id"]).strip())


def collision_fingerprint_for(values: list[str]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1", (table_name,)).fetchone()
    return row is not None
