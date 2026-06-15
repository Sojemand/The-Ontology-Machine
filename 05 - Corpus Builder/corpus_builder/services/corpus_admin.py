"""Owner-local destructive corpus administration flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect, ensure_schema, has_initialized_schema
from ..semantic_release import read_active_snapshot
from .config import load_module_config, resolve_corpus_db_path
from .corpus_admin_confirmation import load_reset_confirmation
from .corpus_admin_sidecars import cleanup_idle_wal_sidecars
from .corpus_admin_sqlite import (
    PROOF_TABLES,
    checkpoint_wal,
    clear_materialized_tables,
    compact_database,
    release_ref,
    table_counts,
)
from .semantic_status import semantic_status


def reset_active_corpus_db(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None = None,
    confirmation_artifact_path: str | Path,
) -> dict[str, Any]:
    """Clear materialized Corpus content while preserving the active release."""

    config = load_module_config(context)
    db_path = Path(resolve_corpus_db_path(context, corpus_db_path, config=config)).resolve()
    confirmation = load_reset_confirmation(confirmation_artifact_path, expected_db_path=db_path)
    if not db_path.exists():
        raise ValueError(f"Corpus DB fehlt: {db_path}")
    previous_status = semantic_status(context, corpus_db_path=db_path)
    conn = connect(str(db_path))
    try:
        if not has_initialized_schema(conn, require_fts=True):
            raise ValueError("Reset-Ziel ist keine initialisierte Corpus Builder DB.")
        ensure_schema(conn)
        previous_snapshot = read_active_snapshot(conn)
        if previous_snapshot is None:
            raise ValueError("Reset erfordert einen aktiven Semantic Release Snapshot.")
        previous_release_ref = release_ref(previous_snapshot)
        previous_counts = table_counts(conn, PROOF_TABLES)
        conn.execute("BEGIN IMMEDIATE")
        cleared_fts_rows = clear_materialized_tables(conn)
        conn.commit()
        physical_compaction = compact_database(conn)
        checkpoint_wal(conn)
        post_snapshot = read_active_snapshot(conn)
        post_release_ref = release_ref(post_snapshot) if post_snapshot is not None else {}
        post_counts = table_counts(conn, PROOF_TABLES)
        semantic_release_preserved = previous_release_ref == post_release_ref and bool(post_release_ref)
        empty_state_proven = all(count == 0 for count in post_counts.values())
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
    post_reset_status = semantic_status(context, corpus_db_path=db_path)
    wal_sidecar_cleanup = cleanup_idle_wal_sidecars(db_path)
    return {
        "status": "ok",
        "corpus_db_path": str(db_path),
        "database_path": str(db_path),
        "removed_files": [],
        "previous_status": previous_status,
        "post_reset_status": post_reset_status,
        "active_release_ref": post_release_ref,
        "preserved_release_ref": previous_release_ref,
        "confirmation": confirmation,
        "cleared_table_counts": previous_counts,
        "cleared_fts_rows": cleared_fts_rows,
        "post_reset_counts": post_counts,
        "semantic_release_preserved": semantic_release_preserved,
        "empty_state_proven": empty_state_proven,
        "physical_compaction": physical_compaction,
        "physical_compaction_performed": bool(physical_compaction.get("performed")),
        "wal_sidecar_cleanup": wal_sidecar_cleanup,
        "active_release_id": post_release_ref.get("release_id"),
        "active_release_version": post_release_ref.get("release_version"),
        "active_release_fingerprint": post_release_ref.get("release_fingerprint"),
        "active_snapshot_id": post_release_ref.get("active_snapshot_id"),
        "runtime_truth_source": "db_snapshot",
    }


__all__ = ["reset_active_corpus_db"]
