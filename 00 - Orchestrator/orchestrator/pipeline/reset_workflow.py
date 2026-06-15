"""Reset workflow for orchestrator pipeline state and artifacts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..models import PipelineLogResetSummary, PipelineSnapshot, ResetSummary, UiState
from . import artifact_repository, debug, storage_repository, validation


def reset_run_history(engine: Any, ui_state: UiState) -> ResetSummary:
    with storage_repository.mutation_lock(engine, "Reset"):
        storage_repository.reload_state(engine)
        engine._modules.close()
        managed_roots = storage_repository.managed_roots(engine, ui_state)
        resettable_records = collect_resettable_records(engine)
        summary = ResetSummary(cleared_records=len(resettable_records))
        for record in resettable_records:
            outcome = restore_source_for_reset(engine, record, ui_state, managed_roots=managed_roots)
            if outcome == "restored":
                summary.restored_sources += 1
            elif outcome == "renamed":
                summary.restored_sources += 1
                summary.renamed_conflicts += 1
        for path in collect_reset_targets(ui_state):
            if remove_reset_target(path):
                summary.removed_targets += 1
        clear_resettable_records(engine, resettable_records)
        engine._snapshot = PipelineSnapshot()
        debug.emit_snapshot(engine)
        if summary.cleared_records or summary.removed_targets:
            debug.append_log(
                engine,
                f"[RESET] {summary.cleared_records} error/abort entries removed, "
                f"{summary.restored_sources} source files restored to input, "
                f"{summary.removed_targets} Error Tree targets deleted",
            )
            if summary.renamed_conflicts:
                debug.append_log(engine, f"[RESET] {summary.renamed_conflicts} source files stored under a new name because of target conflicts")
        else:
            debug.append_log(engine, "[RESET] No old run data found")
        return summary


def reset_pipeline_logs(engine: Any, _ui_state: UiState | None = None) -> PipelineLogResetSummary:
    with storage_repository.mutation_lock(engine, "Reset Pipeline Logs"):
        storage_repository.reload_state(engine)
        engine._modules.close()
        summary = PipelineLogResetSummary(cleared_records=len(engine._state.documents))
        removed_targets: list[str] = []
        for path in collect_pipeline_log_reset_targets(engine):
            if remove_reset_target(path):
                removed_targets.append(_relative_target(engine, path))
        summary.removed_pipeline_targets = tuple(removed_targets)
        storage_repository.reload_state(engine)
        engine._snapshot = PipelineSnapshot()
        debug.emit_snapshot(engine)
        if summary.cleared_records or summary.removed_pipeline_targets:
            debug.append_log(
                engine,
                f"[RESET] {summary.cleared_records} pipeline entries removed, "
                f"{len(summary.removed_pipeline_targets)} hidden pipeline log targets deleted",
            )
        else:
            debug.append_log(engine, "[RESET] No hidden pipeline logs found")
        return summary


def restore_source_for_reset(engine: Any, record: Any, ui_state: UiState, *, managed_roots: tuple[Path, ...]) -> str:
    target_str = record.original_source_path.strip()
    if not target_str:
        return "skipped"
    target_path = Path(target_str)
    input_root = Path(ui_state.input_folder) if ui_state.input_folder.strip() else None
    if input_root is None or not validation.ensure_managed_path(engine, target_path, managed_roots, action="Reset", noun="restore target"):
        return "skipped"
    if not validation.is_within(validation.resolved_path(target_path), validation.resolved_path(input_root)):
        debug.append_log(engine, f"[SECURITY] Reset: restore target outside the input folder is ignored: {target_path}")
        return "skipped"
    current_path = Path(record.source_path.strip()) if record.source_path.strip() else None
    if current_path is None or not current_path.exists():
        if record.current_location != "error_bundle":
            return "skipped"
        return "restored" if target_path.exists() and artifact_repository.path_matches_hash(target_path, record.content_hash) else "skipped"
    if not validation.ensure_managed_path(engine, current_path, managed_roots, action="Reset", noun="current source path"):
        return "skipped"
    if current_path == target_path:
        return "restored" if record.current_location == "error_bundle" else "skipped"
    restored_target = artifact_repository.move_file_with_conflict_handling(engine, current_path, target_path, action="reset", content_hash=record.content_hash, allowed_roots=managed_roots)
    if restored_target is None:
        return "skipped"
    if restored_target != target_path:
        debug.append_log(engine, f"[RESET] Target conflict for {record.relative_path or record.file_name}: {restored_target.name}")
        return "renamed"
    return "restored"


def collect_resettable_records(engine: Any) -> list[Any]:
    return [record for record in engine._state.documents.values() if is_resettable_record(record)]


def is_resettable_record(record: Any) -> bool:
    return record.final_disposition == "error" or record.current_location == "error_bundle" or record.status in {"error", "processing"}


def clear_resettable_records(engine: Any, resettable_records: list[Any]) -> None:
    resettable_hashes = {record.content_hash for record in resettable_records}
    if not resettable_hashes:
        return
    engine._state.documents = {
        content_hash: record
        for content_hash, record in engine._state.documents.items()
        if content_hash not in resettable_hashes
    }
    storage_repository.save_state(engine)


def collect_reset_targets(ui_state: UiState) -> list[Path]:
    candidates = {storage_repository.error_root(ui_state), *storage_repository.legacy_error_roots(ui_state)}
    return sorted(candidates, key=lambda item: (-len(item.parts), str(item)))


def collect_pipeline_log_reset_targets(engine: Any) -> list[Path]:
    return [engine._state_dir]


def remove_reset_target(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return not path.exists()
        path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _relative_target(engine: Any, path: Path) -> str:
    try:
        return path.relative_to(engine._root).as_posix()
    except ValueError:
        return str(path)
