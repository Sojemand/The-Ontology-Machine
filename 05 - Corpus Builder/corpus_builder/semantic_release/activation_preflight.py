"""Activation preflight construction for semantic releases."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import has_initialized_schema
from ..models.types import CorpusConfig
from .activation_confirmation import CONFIRMATION_ARTIFACT_VERSION
from .adapter import load_release_from_path
from .repository import collect_semantic_status, inspect_release_application_compatibility
from .runtime_state import inspect_runtime_release
from .snapshots import (
    build_snapshot_envelope,
    count_stale_documents_for_snapshot,
    recommended_confirmation_filename,
    resolve_runtime_locale,
)


def build_activation_preflight(
    context: ModuleContext,
    config: CorpusConfig,
    *,
    release_path: str | Path,
    corpus_db_path: str | Path,
    conn: sqlite3.Connection | None,
) -> dict[str, Any]:
    resolved_release_path = context.resolve_path(release_path)
    target_release = load_release_from_path(resolved_release_path, stage="source_release")
    next_snapshot = build_snapshot_envelope(target_release, release_path=str(resolved_release_path))
    current_release, current_snapshot, current_release_path, truth_source = inspect_runtime_release(
        context,
        config,
        conn=conn,
    )
    initialized = conn is not None and has_initialized_schema(conn)
    status = collect_semantic_status(conn) if initialized else {"total_documents": 0}
    total_documents = int(status.get("total_documents") or 0)
    compatibility = _inspect_compatibility(conn, target_release, initialized)
    _assert_activation_compatible(compatibility, initialized, total_documents, current_release, next_snapshot)
    current_snapshot_id = str((current_snapshot or {}).get("snapshot_id") or "").strip() or None
    requires_confirmation = current_snapshot is not None and current_snapshot_id != next_snapshot["snapshot_id"] and total_documents > 0
    stale_documents = count_stale_documents_for_snapshot(conn, next_snapshot["snapshot_id"]) if initialized else 0
    return _preflight_payload(
        context,
        config,
        corpus_db_path,
        resolved_release_path,
        current_release,
        current_snapshot,
        current_release_path,
        truth_source,
        next_snapshot,
        compatibility,
        total_documents,
        stale_documents,
        current_snapshot_id,
        requires_confirmation,
        initialized,
    )


def _preflight_payload(
    context: ModuleContext,
    config: CorpusConfig,
    corpus_db_path: str | Path,
    resolved_release_path: Path,
    current_release: dict[str, Any] | None,
    current_snapshot: dict[str, Any] | None,
    current_release_path: str | None,
    truth_source: str,
    next_snapshot: dict[str, Any],
    compatibility: dict[str, Any],
    total_documents: int,
    stale_documents: int,
    current_snapshot_id: str | None,
    requires_confirmation: bool,
    initialized: bool,
) -> dict[str, Any]:
    target_release = next_snapshot["release"]
    current_locale, current_locale_provenance = _runtime_locale_detail(current_release, truth_source)
    next_locale, next_locale_provenance = resolve_runtime_locale(target_release)
    return {
        "current_snapshot": current_snapshot,
        "next_snapshot": next_snapshot,
        "runtime_locale": {
            "current": {"value": current_locale, "provenance": current_locale_provenance},
            "next": {"value": next_locale, "provenance": next_locale_provenance},
        },
        "stale_documents": stale_documents,
        "initialization_required": not initialized or current_snapshot is None,
        "mirror_changes": _mirror_changes(context, config, resolved_release_path, requires_confirmation),
        "db_changes": _db_changes(current_snapshot_id, next_snapshot, truth_source, total_documents, compatibility, stale_documents),
        "allowed_actions": ["cancel", "activate_only", "activate_and_backfill"] if requires_confirmation else ["cancel", "activate_only"],
        "requires_confirmation": requires_confirmation,
        "confirmation_artifact_template": _confirmation_template(corpus_db_path, resolved_release_path, current_snapshot_id, next_snapshot),
        "recommended_confirmation_filename": recommended_confirmation_filename(target_release, snapshot_id=next_snapshot["snapshot_id"]),
        "current_release_path": current_release_path,
        "no_op": current_snapshot_id == next_snapshot["snapshot_id"],
    }


def _inspect_compatibility(
    conn: sqlite3.Connection | None,
    target_release: dict[str, Any],
    initialized: bool,
) -> dict[str, Any]:
    if not initialized or conn is None:
        return {"missing_projection_ids": [], "incompatible_projection_ids": [], "foreign_master_ids": []}
    return inspect_release_application_compatibility(conn, target_release)


def _assert_activation_compatible(
    compatibility: dict[str, Any],
    initialized: bool,
    total_documents: int,
    current_release: dict[str, Any] | None,
    next_snapshot: dict[str, Any],
) -> None:
    if compatibility["missing_projection_ids"]:
        raise ValueError("Semantic Release kann nicht aktiviert werden: aktive Dokumente ohne projection_id vorhanden.")
    if compatibility["foreign_master_ids"]:
        raise ValueError("Semantic Release kann nicht aktiviert werden: aktive Dokumente aus anderer Master-Linie vorhanden.")
    current_master_line = _current_master_taxonomy_release_id(current_release)
    next_master_line = str(next_snapshot["master_taxonomy_release_id"] or "").strip()
    if initialized and total_documents and current_master_line and next_master_line and current_master_line != next_master_line:
        raise ValueError("Semantic Release kann nicht aktiviert werden: unterschiedliche master_taxonomy_release_id.")


def _mirror_changes(
    context: ModuleContext,
    config: CorpusConfig,
    resolved_release_path: Path,
    requires_confirmation: bool,
) -> dict[str, Any]:
    return {
        "published_release_path": str(context.resolve_path(config.semantic.published_release_path)),
        "active_release_path": str(context.resolve_path(config.semantic.active_release_path)),
        "source_release_path": str(resolved_release_path),
        "published_release_will_change": True,
        "active_release_will_change": requires_confirmation,
    }


def _db_changes(
    current_snapshot_id: str | None,
    next_snapshot: dict[str, Any],
    truth_source: str,
    total_documents: int,
    compatibility: dict[str, Any],
    stale_documents: int,
) -> dict[str, Any]:
    return {
        "active_snapshot_id_before": current_snapshot_id,
        "active_snapshot_id_after": next_snapshot["snapshot_id"],
        "runtime_truth_source_before": truth_source,
        "total_documents": total_documents,
        "projection_drift_documents": len(compatibility["incompatible_projection_ids"]),
        "stale_documents_after_activation": stale_documents,
    }


def _confirmation_template(
    corpus_db_path: str | Path,
    resolved_release_path: Path,
    current_snapshot_id: str | None,
    next_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_version": CONFIRMATION_ARTIFACT_VERSION,
        "corpus_db_path": str(corpus_db_path),
        "release_path": str(resolved_release_path),
        "expected_current_snapshot_id": current_snapshot_id,
        "expected_new_snapshot_id": next_snapshot["snapshot_id"],
        "expected_release_fingerprint": next_snapshot["release"]["fingerprint"],
        "expected_master_taxonomy_release_id": str(next_snapshot["master_taxonomy_release_id"] or "").strip(),
        "expected_runtime_locale": next_snapshot["runtime_locale"],
        "decision": "activate_only",
    }


def _current_master_taxonomy_release_id(release: dict[str, Any] | None) -> str | None:
    if not isinstance(release, dict):
        return None
    value = str(release.get("master_taxonomy_release_id") or "").strip()
    return value or None


def _runtime_locale_detail(release: dict[str, Any] | None, runtime_truth_source: str) -> tuple[str | None, str]:
    if not isinstance(release, dict):
        return None, runtime_truth_source
    value, provenance = resolve_runtime_locale(release)
    if runtime_truth_source == "db_snapshot":
        return value, f"{runtime_truth_source}:{provenance}"
    return value, provenance
