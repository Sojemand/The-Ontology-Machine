"""Shared helpers for semantic status and audit flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect_readonly, has_initialized_schema
from ..semantic_release import inspect_runtime_release, installation_state_drift_reason
from ..semantic_release.repository import collect_semantic_status, count_unknown_projection_documents
from .config import load_module_config, resolve_corpus_db_path


def collect_status(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None = None,
) -> tuple[dict[str, Any], bool]:
    config = load_module_config(context)
    db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
    if not Path(db_path).exists():
        return empty_status(), False
    conn = connect_readonly(db_path)
    try:
        if not has_initialized_schema(conn):
            return empty_status(), False
        return collect_semantic_status(conn), True
    finally:
        conn.close()


def count_unknown_documents(context: ModuleContext, *, corpus_db_path: str | Path | None = None) -> int:
    config = load_module_config(context)
    db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
    if not Path(db_path).exists():
        return 0
    conn = connect_readonly(db_path)
    try:
        if not has_initialized_schema(conn):
            return 0
        return count_unknown_projection_documents(conn)
    finally:
        conn.close()


def inspect_release(
    context: ModuleContext,
    *,
    corpus_db_path: str | Path | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None, str]:
    config = load_module_config(context)
    db_path = resolve_corpus_db_path(context, corpus_db_path, config=config)
    if not Path(db_path).exists():
        return inspect_runtime_release(context, config, conn=None)
    conn = connect_readonly(db_path)
    try:
        return inspect_runtime_release(context, config, conn=conn)
    finally:
        conn.close()


def merge_release_state(status: dict[str, Any], release: dict[str, Any] | None) -> None:
    if release is None:
        return
    status["active_release_id"] = status.get("active_release_id") or release.get("release_id")
    status["active_release_version"] = status.get("active_release_version") or release.get("release_version")
    status["active_release_fingerprint"] = status.get("active_release_fingerprint") or release.get("fingerprint")
    status["active_master_taxonomy_release_id"] = (
        status.get("active_master_taxonomy_release_id") or release.get("master_taxonomy_release_id")
    )
    status["active_runtime_locale"] = status.get("active_runtime_locale") or release.get("runtime_locale")
    status["materialization_version"] = status.get("materialization_version") or release.get("materialization_version")


def drift_reason(
    release: dict[str, Any] | None,
    status: dict[str, Any],
    *,
    corpus_db_initialized: bool,
    runtime_truth_source: str,
) -> str | None:
    if runtime_truth_source == "db_snapshot":
        return None
    if corpus_db_initialized:
        return installation_state_drift_reason(release, status) if release is not None else None
    return "corpus_db_uninitialized"


def empty_status() -> dict[str, Any]:
    return {
        "total_documents": 0,
        "stale_documents": 0,
        "active_snapshot_id": None,
        "active_release_id": None,
        "active_release_version": None,
        "active_release_fingerprint": None,
        "active_master_taxonomy_release_id": None,
        "active_runtime_locale": None,
        "integrity_status": None,
        "materialization_version": None,
        "runtime_truth_source": "uninitialized",
    }
