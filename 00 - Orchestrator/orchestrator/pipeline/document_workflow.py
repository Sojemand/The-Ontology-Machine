"""Document attempt helpers shared by serial and stage-based pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..integrations import stage_name_for_module
from ..models import utc_now_iso
from . import (
    artifact_repository,
    debug,
    document_types,
    error_workflow,
    intake_workflow,
    policy,
    runtime_semantics,
    storage_repository,
)


@dataclass(slots=True)
class ActiveRecordContext:
    record: Any
    paths: document_types.DocumentStagePaths
    raw_paths: list[Path] = field(default_factory=list)
    request_paths: list[Path] = field(default_factory=list)
    structured_paths: list[Path] = field(default_factory=list)
    validation_paths: list[Path] = field(default_factory=list)
    normalized_paths: list[Path] = field(default_factory=list)


def start_record_attempt(engine: Any, record: Any, ctx: Any) -> ActiveRecordContext | None:
    if getattr(ctx, "runtime_semantics", None) is None:
        runtime_semantics.ensure_initialized(engine, ctx)
    else:
        runtime_semantics.restore_stage(engine, ctx)
    lock = getattr(engine, "_runtime_lock", None)
    if lock is None:
        _mark_attempt_started(engine, record)
    else:
        with lock:
            _mark_attempt_started(engine, record)
    storage_repository.save_state(engine)
    debug.append_log(engine, f"[START] {record.relative_path} (attempt {record.attempts})")
    debug.emit_snapshot(engine)
    if not intake_workflow.prepare_record_for_processing(engine, record, ctx, emit_stage=True):
        return None
    paths = document_types.build_document_stage_paths(engine, record, ctx)
    try:
        document_types.prepare_document_runtime(engine, record, paths, allowed_roots=ctx.managed_roots)
    except Exception as exc:
        error_workflow.handle_failure(
            engine,
            record,
            ctx,
            stage_name_for_module(record.optimizer_module_key or "optimizer"),
            f"Working directory could not be prepared: {exc}",
        )
        cleanup_attempt_runtime(engine, ActiveRecordContext(record=record, paths=paths), ctx)
        return None
    debug.set_active_document_log_path(engine, paths.working_log_path)
    debug.append_log(engine, f"[DOC] {record.relative_path}: working tree prepared")
    return ActiveRecordContext(record=record, paths=paths)


def cleanup_attempt_runtime(engine: Any, active: ActiveRecordContext, ctx: Any) -> None:
    artifact_repository.remove_file(engine, active.paths.working_source_path, allowed_roots=ctx.managed_roots)
    artifact_repository.remove_file(engine, active.paths.working_log_path, allowed_roots=ctx.managed_roots)
    debug.set_active_document_log_path(engine, None)


def cancel_record_attempt(engine: Any, active: ActiveRecordContext, ctx: Any, *, stage_name: str = "") -> None:
    stage = stage_name or _active_stage_name(engine, active.record)
    active.record.failed_attempts += 1
    debug.set_stage(engine, stage, "Aborted", "Processing aborted")
    error_workflow.route_to_error(engine, active.record, ctx, stage=stage, reason="Processing aborted", final=True)


def _mark_attempt_started(engine: Any, record: Any) -> None:
    record.attempts += 1
    if record.attempts > 1:
        engine._snapshot.retries += 1
    record.status = "processing"
    record.final_disposition = ""
    record.last_error = ""
    policy.clear_record_review_state(record)
    record.normalizer_failed_attempts = 0
    record.artifacts.clear_normal_outputs()
    record.last_processed_at = utc_now_iso()
    record.touch()
    engine._snapshot.current_file = record.relative_path or record.file_name
    engine._snapshot.current_attempt = record.attempts


def _active_stage_name(engine: Any, record: Any) -> str:
    for name, snapshot in engine._snapshot.stage_statuses.items():
        if snapshot.status == "Processing...":
            return name
    return record.last_stage or "Intake"
