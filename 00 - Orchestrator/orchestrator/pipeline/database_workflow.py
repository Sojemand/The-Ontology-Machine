"""Database creation flows for the Orchestrator UI."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..integrations import stage_name_for_module
from ..models import utc_now_iso
from . import artifact_repository, debug, runtime_retention, storage_repository


def run_create_database(engine: Any, ui_state: Any, *, request: dict[str, Any]) -> dict[str, Any]:
    with storage_repository.mutation_lock(engine, "Create Database"):
        storage_repository.reload_state(engine)
        runtime_dir = engine._runtime_root / (
            f"create-database-{_safe_stage_name(_text(request.get('database_name')) or 'database')}-{utc_now_iso().replace(':', '-')}"
        )
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
        previous_log_path = engine._active_log_path
        engine._active_log_path = runtime_dir / "run.log"
        debug.reset_snapshot(engine, total=0)
        debug.append_log(engine, f"Database creation started: {_text(request.get('target_db_path'))}")
        try:
            result = _execute_create_database(engine, ui_state=ui_state, request=request, runtime_dir=runtime_dir)
        finally:
            engine._snapshot.is_running = False
            debug.emit_snapshot(engine)
            artifact_repository.prune_empty_dirs(runtime_dir, stop_at=(engine._state_dir,))
            artifact_repository.prune_empty_dirs(engine._runtime_root, stop_at=(engine._state_dir,))
            debug.append_log(engine, "Database creation finished")
            runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
            engine._active_log_path = previous_log_path
        return result


def _execute_create_database(engine: Any, *, ui_state: Any, request: dict[str, Any], runtime_dir: Path) -> dict[str, Any]:
    stage_name = stage_name_for_module("corpus_builder")
    target_db_path = Path(_require_text(request.get("target_db_path"), "target_db_path"))
    bootstrap_mode = _text(request.get("bootstrap_mode")) or "default_release"
    database_name = _text(request.get("database_name")) or target_db_path.stem
    debug.set_stage(engine, stage_name, "Processing...", target_db_path.name)
    debug.emit_snapshot(engine)
    _ensure_new_database_target(target_db_path)
    if bootstrap_mode == "default_release":
        blueprint_ref = _text(request.get("blueprint_ref")) or "default"
        taxonomy_locale = _text(request.get("taxonomy_locale")) or None
        release_basename = _safe_stage_name(blueprint_ref)
        if taxonomy_locale:
            release_basename = f"{release_basename}__{_safe_stage_name(taxonomy_locale)}"
        release_path = _semantic_release_output_dir(ui_state, runtime_dir) / f"{release_basename}.semantic_release.json"
        release_path.parent.mkdir(parents=True, exist_ok=True)
        blueprint_detail = engine.export_default_blueprint_release(
            blueprint_ref=blueprint_ref,
            target_locale=taxonomy_locale,
            output_path=release_path,
        )
        exported_release_path = Path(_require_text(blueprint_detail.get("output_path"), "output_path"))
        _create_empty_database(target_db_path)
        try:
            result = engine._modules.activate_semantic_release(exported_release_path, target_db_path)
        except Exception:
            _remove_created_database_files(target_db_path)
            raise
        if result.status != "applied":
            _remove_created_database_files(target_db_path)
            detail = f"Database could not be created: {result.reason or 'Release activation failed.'}"
            debug.set_stage(engine, stage_name, "Error", detail)
            debug.append_log(engine, f"[DB-ERROR] {detail}")
            debug.emit_snapshot(engine)
            raise RuntimeError(detail)
        detail = (
            f"Database created | {target_db_path.name} | "
            f"Blueprint {blueprint_ref} | Locale {blueprint_detail.get('runtime_locale') or taxonomy_locale or '-'} | "
            f"Release {result.release_id or exported_release_path.name} | {result.release_version or '-'}"
        )
        payload = {
            "database_name": database_name,
            "target_db_path": str(target_db_path),
            "bootstrap_mode": bootstrap_mode,
            "blueprint_ref": blueprint_ref,
            "taxonomy_locale": str(blueprint_detail.get("runtime_locale") or taxonomy_locale or ""),
            "release_id": result.release_id,
            "release_version": result.release_version,
            "active_snapshot_id": result.active_snapshot_id,
            "release_path": str(exported_release_path),
        }
    else:
        _create_empty_database(target_db_path)
        detail = f"Database created | {target_db_path.name} | without active release"
        payload = {
            "database_name": database_name,
            "target_db_path": str(target_db_path),
            "bootstrap_mode": bootstrap_mode,
            "blueprint_ref": "",
            "taxonomy_locale": "",
            "release_id": "",
            "release_version": "",
            "active_snapshot_id": "",
            "release_path": "",
        }
    debug.set_stage(engine, stage_name, "Done", detail)
    debug.append_log(engine, f"[DB] {detail}")
    debug.emit_snapshot(engine)
    return payload


def _ensure_new_database_target(target_db_path: Path) -> None:
    for path in (
        target_db_path,
        target_db_path.with_name(f"{target_db_path.name}-wal"),
        target_db_path.with_name(f"{target_db_path.name}-shm"),
    ):
        if path.exists():
            raise ValueError(f"Target database already exists: {target_db_path}")


def _create_empty_database(target_db_path: Path) -> None:
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_db_path))
    conn.close()


def _remove_created_database_files(target_db_path: Path) -> None:
    for path in (
        target_db_path,
        target_db_path.with_name(f"{target_db_path.name}-wal"),
        target_db_path.with_name(f"{target_db_path.name}-shm"),
    ):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def _semantic_release_output_dir(ui_state: Any, runtime_dir: Path) -> Path:
    artifact_text = str(getattr(ui_state, "artifact_folder", "") or "").strip()
    if artifact_text:
        return Path(artifact_text) / "Semantic Release"
    return runtime_dir


def _require_text(value: Any, label: str) -> str:
    text = _text(value)
    if not text:
        raise ValueError(f"{label} is missing.")
    return text


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_stage_name(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-._" else "-" for ch in value)
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-.") or "database"


__all__ = ["run_create_database"]
