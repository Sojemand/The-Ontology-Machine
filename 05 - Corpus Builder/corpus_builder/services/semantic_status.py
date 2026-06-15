"""Status and audit flows for semantic corpus services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect_readonly, has_initialized_schema
from ..semantic_release import (
    analyze_release,
    load_published_release,
    load_release_from_path,
    write_release_analysis,
)
from .config import load_module_config, resolve_corpus_db_path
from .semantic_status_context import (
    collect_status,
    count_unknown_documents,
    drift_reason,
    inspect_release,
    merge_release_state,
)


def semantic_status(context: ModuleContext, *, corpus_db_path: str | Path | None = None) -> dict[str, Any]:
    config = load_module_config(context)
    active_path = context.resolve_path(config.semantic.active_release_path)
    published_path = context.resolve_path(config.semantic.published_release_path)
    release, active_snapshot, runtime_release_path, runtime_truth_source = inspect_release(
        context,
        corpus_db_path=corpus_db_path,
    )
    published_release = load_release_from_path(published_path, stage="published_release") if published_path.exists() else None
    if release is not None:
        analysis = analyze_release(release)
    else:
        analysis = {"projection_count": 0, "issues": ["Kein aktiver Semantic Release angewendet."], "warnings": []}

    status, corpus_db_initialized = collect_status(context, corpus_db_path=corpus_db_path)
    current_drift_reason = drift_reason(
        release,
        status,
        corpus_db_initialized=corpus_db_initialized,
        runtime_truth_source=runtime_truth_source,
    )
    merge_release_state(status, release)
    status["runtime_truth_source"] = runtime_truth_source
    status.update(
        {
            "active_release_path": str(active_path),
            "published_release_path": str(published_path),
            "published_release_id": published_release.get("release_id") if published_release else None,
            "published_release_version": published_release.get("release_version") if published_release else None,
            "published_release_fingerprint": published_release.get("fingerprint") if published_release else None,
            "pending_release_change": bool(
                published_release
                and (
                    release is None
                    or str(published_release.get("fingerprint") or "") != str(release.get("fingerprint") or "")
                )
            ),
            "active_release_state_matches_installation_state": current_drift_reason is None,
            "installation_state_drift_reason": current_drift_reason,
            "release_analysis": analysis,
            "active_release_runtime_path": runtime_release_path,
            "active_snapshot": active_snapshot,
        }
    )
    return status


def read_active_semantic_release(context: ModuleContext, *, corpus_db_path: str | Path | None = None) -> dict[str, Any]:
    release, active_snapshot, release_path, _runtime_truth_source = inspect_release(
        context,
        corpus_db_path=corpus_db_path,
    )
    if release is None or not release_path:
        config = load_module_config(context)
        db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
        if Path(db_path).exists():
            conn = connect_readonly(db_path)
            try:
                if has_initialized_schema(conn):
                    raise ValueError(
                        "Initialisierte corpus.db enthaelt keinen gueltigen active_snapshot. Semantic Release erneut aktivieren."
                    )
            finally:
                conn.close()
        raise ValueError(
            "Kein aktiver Semantic Release vorhanden. Wende zuerst den veroeffentlichten Release an."
        )
    return {
        "status": semantic_status(context, corpus_db_path=corpus_db_path),
        "release": release,
        "release_id": release.get("release_id"),
        "release_version": release.get("release_version"),
        "fingerprint": release.get("fingerprint"),
        "release_path": str(release_path),
        "master_taxonomy_release_id": release.get("master_taxonomy_release_id"),
        "runtime_locale": release.get("runtime_locale"),
        "active_snapshot": active_snapshot,
    }


def audit_semantics(context: ModuleContext, *, corpus_db_path: str | Path | None = None) -> dict[str, Any]:
    config = load_module_config(context)
    active_path = context.resolve_path(config.semantic.active_release_path)
    release, published_path = load_published_release(context, config)
    analysis = analyze_release(release)
    report_path = write_release_analysis(context, config, analysis)
    active_release, _active_snapshot, _runtime_release_path, runtime_truth_source = inspect_release(
        context,
        corpus_db_path=corpus_db_path,
    )
    status, corpus_db_initialized = collect_status(context, corpus_db_path=corpus_db_path)
    current_drift_reason = drift_reason(
        active_release,
        status,
        corpus_db_initialized=corpus_db_initialized,
        runtime_truth_source=runtime_truth_source,
    )
    merge_release_state(status, active_release)
    status["unknown_projection_documents"] = count_unknown_documents(context, corpus_db_path=corpus_db_path)
    status["audit_issue_count"] = len(analysis.get("issues") or [])
    status["audit_warning_count"] = len(analysis.get("warnings") or [])
    status["active_release_state_matches_installation_state"] = current_drift_reason is None
    status["installation_state_drift_reason"] = current_drift_reason
    status["runtime_truth_source"] = runtime_truth_source
    return {
        "release_path": str(published_path),
        "release_origin": "published",
        "report_path": str(report_path),
        "analysis": analysis,
        "status": status,
    }


__all__ = ["audit_semantics", "read_active_semantic_release", "semantic_status"]
