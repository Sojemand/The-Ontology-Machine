"""Snapshot, logging and cancellation helpers for pipeline runs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .. import bounded_log
from ..models import PipelineSnapshot, StageSnapshot, utc_now_iso
from ..models.snapshots import default_stage_statuses
from .exceptions import OrchestratorCancelled

logger = logging.getLogger(__name__)
PIPELINE_LOG_BYTES_HARD_CAP = 5 * 1024 * 1024


def _runtime_lock(engine: Any):
    return getattr(engine, "_runtime_lock", None)


def active_document_log_path(engine: Any) -> Path | None:
    thread_local = getattr(engine, "_thread_local", None)
    path = getattr(thread_local, "active_document_log_path", None) if thread_local is not None else None
    return path if isinstance(path, Path) else None


def set_active_document_log_path(engine: Any, path: Path | None) -> None:
    thread_local = getattr(engine, "_thread_local", None)
    if thread_local is None:
        return
    if path is None:
        if hasattr(thread_local, "active_document_log_path"):
            delattr(thread_local, "active_document_log_path")
        return
    thread_local.active_document_log_path = Path(path)


def reset_snapshot(engine: Any, *, total: int) -> None:
    lock = _runtime_lock(engine)
    if lock is None:
        engine._snapshot = PipelineSnapshot(
            total=total,
            completed=0,
            pending=total,
            success=0,
            errors=0,
            needs_review=0,
            retries=0,
            current_file="",
            current_attempt=0,
            is_running=True,
            aborted=False,
            stage_statuses=default_stage_statuses(),
        )
    else:
        with lock:
            engine._snapshot = PipelineSnapshot(
                total=total,
                completed=0,
                pending=total,
                success=0,
                errors=0,
                needs_review=0,
                retries=0,
                current_file="",
                current_attempt=0,
                is_running=True,
                aborted=False,
                stage_statuses=default_stage_statuses(),
            )
    emit_snapshot(engine)


def reset_stage_statuses(engine: Any) -> None:
    lock = _runtime_lock(engine)
    if lock is None:
        engine._snapshot.stage_statuses = default_stage_statuses()
        return
    with lock:
        engine._snapshot.stage_statuses = default_stage_statuses()


def recompute_snapshot_counts(engine: Any, tracked_hashes: set[str]) -> None:
    lock = _runtime_lock(engine)
    if lock is None:
        documents = [engine._state.documents[key] for key in tracked_hashes if key in engine._state.documents]
        success = sum(1 for record in documents if record.final_disposition in {"success", "needs_review"})
        needs_review = sum(1 for record in documents if record.final_disposition == "needs_review")
        errors = sum(1 for record in documents if record.status == "error")
        completed = success
        engine._snapshot.success = success
        engine._snapshot.needs_review = needs_review
        engine._snapshot.errors = errors
        engine._snapshot.completed = completed
        engine._snapshot.pending = max(engine._snapshot.total - completed - errors, 0)
        return
    with lock:
        documents = [engine._state.documents[key] for key in tracked_hashes if key in engine._state.documents]
        success = sum(1 for record in documents if record.final_disposition in {"success", "needs_review"})
        needs_review = sum(1 for record in documents if record.final_disposition == "needs_review")
        errors = sum(1 for record in documents if record.status == "error")
        completed = success
        engine._snapshot.success = success
        engine._snapshot.needs_review = needs_review
        engine._snapshot.errors = errors
        engine._snapshot.completed = completed
        engine._snapshot.pending = max(engine._snapshot.total - completed - errors, 0)


def emit_snapshot(engine: Any) -> None:
    if engine._snapshot_callback:
        lock = _runtime_lock(engine)
        if lock is None:
            engine._snapshot_callback(engine._snapshot)
            return
        with lock:
            engine._snapshot_callback(engine._snapshot)


def append_log(engine: Any, line: str, *, document_log_path: Path | None = None) -> None:
    logger.info(line)
    active_paths: list[Path] = []
    for path in (engine._active_log_path, document_log_path or active_document_log_path(engine)):
        if path is None or path in active_paths:
            continue
        active_paths.append(path)
    lock = _runtime_lock(engine)
    if lock is None:
        for path in active_paths:
            _write_log_line(path, line)
    else:
        with lock:
            for path in active_paths:
                _write_log_line(path, line)
    if engine._log_callback:
        engine._log_callback(line)


def _write_log_line(path: Path, line: str) -> None:
    try:
        bounded_log.append_text(path, f"{utc_now_iso()} {line}\n", max_bytes=PIPELINE_LOG_BYTES_HARD_CAP)
    except Exception:
        logger.warning("Could not write log: %s", path, exc_info=True)


def set_stage(
    engine: Any,
    name: str,
    status: str,
    detail: str = "",
    *,
    progress_current: int = 0,
    progress_total: int = 0,
    progress_label: str = "",
) -> None:
    lock = _runtime_lock(engine)
    snapshot_value = StageSnapshot(
        status=str(status or "").strip() or "Ready",
        detail="" if detail is None else str(detail),
        progress_current=max(int(progress_current), 0),
        progress_total=max(int(progress_total), 0),
        progress_label=str(progress_label or "").strip(),
    )
    if lock is None:
        engine._snapshot.stage_statuses[name] = snapshot_value
        return
    with lock:
        engine._snapshot.stage_statuses[name] = snapshot_value


def check_cancelled(engine: Any) -> None:
    if engine._cancel_requested and engine._cancel_requested():
        lock = _runtime_lock(engine)
        if lock is None:
            engine._snapshot.aborted = True
        else:
            with lock:
                engine._snapshot.aborted = True
        raise OrchestratorCancelled()
