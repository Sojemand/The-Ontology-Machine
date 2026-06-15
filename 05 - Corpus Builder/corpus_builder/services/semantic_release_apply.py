"""Semantic release activation flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect, ensure_schema
from ..models.serialization import atomic_json_write
from ..semantic_release import (
    analyze_release,
    assert_default_release_write_allowed,
    assert_release_can_be_applied,
    build_activation_preflight,
    load_release_from_path,
    read_active_snapshot,
    validate_activation_confirmation,
    write_release_analysis,
)
from ..semantic_release.repository import apply_release_installation_state
from ..semantic_release.snapshots import count_stale_documents_for_snapshot, sync_materialization_state_mirrors, write_snapshot
from .config import load_module_config, resolve_corpus_db_path
from .semantic_release_alignment import align_initial_activation_payload_headers
from .semantic_release_mirrors import read_existing_bytes, restore_release_file


def apply_semantic_release(
    context: ModuleContext,
    *,
    release_path: str | Path | None = None,
    corpus_db_path: str | Path | None = None,
    confirmation_artifact_path: str | Path | None = None,
    write_global_mirrors: bool = True,
) -> dict[str, Any]:
    config = load_module_config(context)
    published_path = context.resolve_path(config.semantic.published_release_path)
    active_path = context.resolve_path(config.semantic.active_release_path)
    resolved_release_path = context.resolve_path(release_path) if release_path is not None else published_path
    release_stage = "source_release" if release_path is not None else "published_release"
    release = load_release_from_path(resolved_release_path, stage=release_stage)
    if write_global_mirrors:
        assert_default_release_write_allowed(published_path, release)
    analysis = analyze_release(release)
    report_path = write_release_analysis(context, config, analysis) if write_global_mirrors else None
    db_path = Path(resolve_corpus_db_path(context, corpus_db_path, config=config))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    activation = _apply_release_to_database(
        context=context,
        config=config,
        release=release,
        release_path=resolved_release_path,
        db_path=db_path,
        confirmation_artifact_path=confirmation_artifact_path,
        mirror_paths=(published_path, active_path),
        write_global_mirrors=write_global_mirrors,
    )
    if activation.pop("needs_backfill", False):
        activation.update(_run_activation_backfill(context, db_path))
    return _activation_result(
        release=release,
        release_path=resolved_release_path,
        published_path=published_path,
        active_path=active_path,
        report_path=report_path,
        analysis=analysis,
        write_global_mirrors=write_global_mirrors,
        **activation,
    )


def _apply_release_to_database(
    *,
    context: ModuleContext,
    config,
    release: dict[str, Any],
    release_path: Path,
    db_path: Path,
    confirmation_artifact_path: str | Path | None,
    mirror_paths: tuple[Path, Path],
    write_global_mirrors: bool,
) -> dict[str, Any]:
    published_path, active_path = mirror_paths
    previous_published_bytes = read_existing_bytes(published_path)
    previous_active_bytes = read_existing_bytes(active_path)
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        assert_release_can_be_applied(conn, release)
        preflight = build_activation_preflight(context, config, release_path=release_path, corpus_db_path=str(db_path), conn=conn)
        decision = validate_activation_confirmation(
            artifact_path=confirmation_artifact_path,
            preflight=preflight,
            corpus_db_path=str(db_path),
        )
        current_snapshot = read_active_snapshot(conn)
        if preflight.get("no_op") and confirmation_artifact_path is None:
            snapshot_id = str((current_snapshot or {}).get("snapshot_id") or "")
            return _no_op_activation(snapshot_id=snapshot_id, stale_documents=int(preflight.get("stale_documents") or 0))
        snapshot = write_snapshot(conn, release, release_path=str(release_path))
        apply_release_installation_state(conn, snapshot)
        aligned_count = align_initial_activation_payload_headers(conn, release, current_snapshot=current_snapshot)
        sync_materialization_state_mirrors(conn, snapshot["snapshot_id"])
        stale_documents = count_stale_documents_for_snapshot(conn, snapshot["snapshot_id"])
        _write_mirrors_if_enabled(conn, release, mirror_paths, previous_published_bytes, previous_active_bytes, write_global_mirrors)
        conn.commit()
        return {
            "active_snapshot_id": snapshot["snapshot_id"],
            "stale_documents": stale_documents,
            "backfill_started": decision == "activate_and_backfill",
            "backfill_processed_count": 0,
            "initial_payload_headers_aligned_count": aligned_count,
            "no_op": False,
            "global_mirrors_written": bool(write_global_mirrors),
            "needs_backfill": decision == "activate_and_backfill",
        }
    except Exception as exc:
        conn.rollback()
        if write_global_mirrors:
            restore_release_file(published_path, previous_published_bytes, cause=exc)
            restore_release_file(active_path, previous_active_bytes, cause=exc)
        raise
    finally:
        conn.close()


def _write_mirrors_if_enabled(
    conn,
    release: dict[str, Any],
    mirror_paths: tuple[Path, Path],
    previous_published_bytes: bytes | None,
    previous_active_bytes: bytes | None,
    write_global_mirrors: bool,
) -> None:
    if not write_global_mirrors:
        return
    published_path, active_path = mirror_paths
    try:
        atomic_json_write(published_path, release)
        atomic_json_write(active_path, release)
    except Exception:
        conn.rollback()
        restore_release_file(published_path, previous_published_bytes)
        restore_release_file(active_path, previous_active_bytes)
        raise


def _run_activation_backfill(context: ModuleContext, db_path: Path) -> dict[str, int]:
    from .semantic_backfill import backfill_semantics
    from .semantic_status import semantic_status

    backfill_result = backfill_semantics(context, corpus_db_path=db_path, stale_only=True)
    return {
        "backfill_processed_count": int(backfill_result.get("processed_count") or 0),
        "stale_documents": int(semantic_status(context, corpus_db_path=db_path).get("stale_documents") or 0),
    }


def _no_op_activation(*, snapshot_id: str, stale_documents: int) -> dict[str, Any]:
    return {
        "active_snapshot_id": snapshot_id or None,
        "stale_documents": stale_documents,
        "backfill_started": False,
        "backfill_processed_count": 0,
        "initial_payload_headers_aligned_count": 0,
        "no_op": True,
        "global_mirrors_written": False,
        "needs_backfill": False,
    }


def _activation_result(
    *,
    release: dict[str, Any],
    release_path: Path,
    published_path: Path,
    active_path: Path,
    report_path: Path | None,
    analysis: dict[str, Any],
    write_global_mirrors: bool,
    **activation: Any,
) -> dict[str, Any]:
    return {
        "status": "applied",
        "release_id": release.get("release_id"),
        "release_version": release.get("release_version"),
        "fingerprint": release.get("fingerprint"),
        "release_fingerprint": release.get("release_fingerprint") or release.get("fingerprint"),
        "release_path": str(release_path),
        "published_release_path": str(published_path),
        "active_release_path": str(active_path),
        "report_path": str(report_path) if report_path is not None else None,
        "analysis": analysis,
        "global_mirrors_written": bool(write_global_mirrors),
        **activation,
    }
