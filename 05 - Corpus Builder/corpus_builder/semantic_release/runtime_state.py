"""Runtime-truth resolution for semantic releases."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..context import ModuleContext
from ..database import has_initialized_schema
from ..models.types import CorpusConfig
from .adapter import load_active_release
from .policy import installation_state_drift_reason
from .repository import apply_release_installation_state, collect_semantic_status
from .snapshots import read_active_snapshot, sync_materialization_state_mirrors, write_snapshot


def inspect_runtime_release(
    context: ModuleContext,
    config: CorpusConfig,
    *,
    conn: sqlite3.Connection | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None, str]:
    if conn is not None and has_initialized_schema(conn):
        active_snapshot = read_active_snapshot(conn)
        if active_snapshot is None:
            status = collect_semantic_status(conn)
            if not status.get("active_release_fingerprint"):
                return None, None, None, "uninitialized"
            raise ValueError(
                "Initialisierte corpus.db enthaelt keinen gueltigen active_snapshot. "
                "Semantic Release erneut aktivieren."
            )
        release = dict(active_snapshot["release"])
        return release, active_snapshot, str(active_snapshot["release_path"]), "db_snapshot"
    active_path = context.resolve_path(config.semantic.active_release_path)
    if not active_path.exists():
        return None, None, None, "uninitialized"
    release, resolved_active_path = load_active_release(context, config)
    return dict(release), None, str(resolved_active_path), "filesystem_release"


def ensure_mutation_runtime_release(
    conn: sqlite3.Connection,
    context: ModuleContext,
    config: CorpusConfig,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    active_snapshot = read_active_snapshot(conn)
    if active_snapshot is not None:
        return dict(active_snapshot["release"]), active_snapshot, False
    release, active_path = load_active_release(context, config)
    status = collect_semantic_status(conn)
    drift_reason = installation_state_drift_reason(release, status)
    if status["total_documents"] and drift_reason not in (None, "installation_state_missing_active_release"):
        raise ValueError(
            "Legacy corpus.db kann ohne explizite Re-Aktivierung nicht snapshot-seeded werden: "
            f"{drift_reason}"
        )
    snapshot = write_snapshot(conn, release, release_path=str(active_path))
    apply_release_installation_state(conn, snapshot)
    sync_materialization_state_mirrors(conn, snapshot["snapshot_id"])
    return dict(snapshot["release"]), snapshot, True
