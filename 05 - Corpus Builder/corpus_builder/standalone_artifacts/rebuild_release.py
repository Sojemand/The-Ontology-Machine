"""Release and database preparation helpers for artifact-tree rebuilds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..context import ModuleContext
from ..database import connect, ensure_schema, has_initialized_schema
from ..models.types import LoadBundle
from ..semantic_release import inspect_runtime_release, load_release_from_path, validate_payload_against_release
from ..semantic_release.repository import apply_release_installation_state
from ..semantic_release.snapshots import read_active_snapshot, sync_materialization_state_mirrors, write_snapshot
from ..services.config import resolve_corpus_db_path


def validate_rebuild_payloads(bundles: list[LoadBundle], release: dict[str, Any]) -> None:
    incompatible_files: list[str] = []
    for bundle in bundles:
        payload = json.loads(bundle.normalized_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            incompatible_files.append(f"{bundle.normalized_path.name}: normalized.json muss ein Objekt sein.")
            continue
        try:
            validate_payload_against_release(payload, release)
        except ValueError as exc:
            incompatible_files.append(f"{bundle.normalized_path.name}: {exc}")
    if incompatible_files:
        raise ValueError(f"Rebuild abgebrochen: {' | '.join(incompatible_files[:5])}")


def replace_existing_db_files(db_path: Path) -> bool:
    replaced_existing = False
    for target in (db_path, db_path.with_name(f"{db_path.name}-shm"), db_path.with_name(f"{db_path.name}-wal")):
        if target.exists():
            target.unlink()
            replaced_existing = True
    return replaced_existing


def seed_rebuild_release_snapshot(
    db_path: Path,
    release: dict[str, Any],
    *,
    release_path: str,
) -> bool:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        active_snapshot = read_active_snapshot(conn)
        if active_snapshot is not None:
            active_fingerprint = str(active_snapshot["release"].get("fingerprint") or "").strip()
            release_fingerprint = str(release.get("fingerprint") or "").strip()
            if active_fingerprint != release_fingerprint:
                raise ValueError(
                    "Rebuild-DB enthaelt bereits einen anderen aktiven Semantic Release: "
                    f"{active_fingerprint} != {release_fingerprint}"
                )
            return False
        snapshot = write_snapshot(conn, release, release_path=release_path)
        apply_release_installation_state(conn, snapshot)
        sync_materialization_state_mirrors(conn, snapshot["snapshot_id"])
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resolve_rebuild_release(
    context: ModuleContext,
    *,
    config,
    corpus_db_path: str | Path | None,
    release_path: str | Path | None,
    replace_existing: bool,
) -> tuple[dict[str, Any], str]:
    if release_path is not None and str(release_path).strip():
        resolved_release_path = context.resolve_path(release_path)
        return load_release_from_path(resolved_release_path, stage="rebuild_release"), str(resolved_release_path)
    resolved_db_path = Path(resolve_corpus_db_path(context, corpus_db_path, config=config))
    if resolved_db_path.exists() and not replace_existing:
        conn = connect(str(resolved_db_path))
        try:
            if has_initialized_schema(conn):
                release, _active_snapshot, release_path, _runtime_truth_source = inspect_runtime_release(context, config, conn=conn)
                if release is not None and release_path:
                    return release, release_path
            ensure_schema(conn)
        finally:
            conn.close()
    release, _active_snapshot, release_path, _runtime_truth_source = inspect_runtime_release(context, config, conn=None)
    if release is None or not release_path:
        raise ValueError(
            "Kein aktiver Semantic Release vorhanden. Wende zuerst den veroeffentlichten Release an."
        )
    return release, release_path
