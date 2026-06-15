"""Backfill flows for semantic corpus services."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext
from ..database import connect, ensure_schema
from ..loader import rematerialize_document
from ..semantic_release import ensure_mutation_runtime_release
from ..semantic_release.repository import (
    complete_materialization_run,
    create_materialization_run,
    select_backfill_document_ids,
)
from .config import load_module_config, resolve_corpus_db_path


def backfill_semantics(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None = None,
    document_ids: list[str] | None = None,
    stale_only: bool = True,
    limit: int | None = None,
) -> dict[str, object]:
    config = load_module_config(context)
    db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        release, _active_snapshot, _seeded = ensure_mutation_runtime_release(conn, context, config)
        target_ids = select_backfill_document_ids(conn, document_ids=document_ids, stale_only=stale_only, limit=limit)
        run_id = create_materialization_run(
            conn,
            action="backfill",
            release_version=str(release.get("release_version") or ""),
            scope="selected_documents" if document_ids else ("stale_only" if stale_only else "all_documents"),
            notes=f"requested={len(target_ids)}",
        )
        conn.commit()
        processed, errors = _rematerialize_documents(conn, target_ids, release)
        complete_materialization_run(conn, run_id=run_id, processed_count=processed, stale_count=len(target_ids), error_count=errors)
        conn.commit()
    finally:
        conn.close()
    return {
        "run_id": run_id,
        "processed_count": processed,
        "stale_count": len(target_ids),
        "error_count": errors,
        "release_version": release.get("release_version"),
    }


def _rematerialize_documents(conn, document_ids: list[str], release: dict[str, object]) -> tuple[int, int]:
    processed = 0
    errors = 0
    for doc_id in document_ids:
        item = rematerialize_document(conn, doc_id, release)
        if item.status == "loaded":
            processed += 1
        else:
            errors += 1
    return processed, errors


__all__ = ["backfill_semantics"]
