"""Workflow stage for orchestrator UI actions."""

from __future__ import annotations

from ..main.workflow import reset_logging_files
from . import dialogs, queue_scheduler, repository, validation
from .types import RESET_PIPELINE_LOGS_WORKER_ACTION, RESET_WORKER_ACTION, RUN_WORKER_ACTION
from .workflow_artifact_tree import (
    _apply_artifact_tree_refs,
    _artifact_tree_name,
    _artifact_tree_parent,
    _artifact_tree_refs,
    _build_create_artifact_tree_request,
    _suggest_artifact_tree_dialog_values,
    create_artifact_tree,
)
from .workflow_database import (
    _build_create_database_request,
    _load_default_blueprints,
    _safe_database_file_name,
    _target_database_path,
    create_database,
)
from .workflow_database_status import _database_status_placeholder, _release_label, refresh_database_status
from .workflow_release import _load_release_preflight, _resolve_activation_confirmation, activate_selected_release
from .workflow_runtime import (
    _check_worker_lifecycle,
    _drain_worker_queue,
    abort_processing,
    active_stage_name,
    close_app,
    finish_worker,
    force_stop_worker,
    mark_snapshot_aborted,
    start_worker,
    wait_for_worker_exit,
)


def start_processing(app) -> None:
    app._flush_pending_saves()
    app._save_ui_state()
    fields = repository.read_fields(app)
    try:
        validation.ensure_startable(fields)
        app._save_runtime_settings()
        app._start_worker(action=RUN_WORKER_ACTION, ui_state=fields.to_ui_state())
    except Exception as exc:
        app._append_log(f"[ERROR] Start failed: {exc}")
        dialogs.show_error(str(exc))


def reset_run_history(app) -> None:
    if app._processing or not dialogs.confirm_reset(app):
        return
    app._flush_pending_saves()
    app._save_ui_state()
    try:
        app._clear_log()
        app._start_worker(action=RESET_WORKER_ACTION, ui_state=app._current_ui_state())
    except Exception as exc:
        app._append_log(f"[ERROR] Reset failed: {exc}")
        dialogs.show_error(str(exc))


def reset_pipeline_logs(app) -> None:
    if app._processing or not dialogs.confirm_reset_pipeline_logs(app):
        return
    app._flush_pending_saves()
    app._save_ui_state()
    try:
        app._clear_log()
        reset_logging_files(app._state_dir)
        app._start_worker(action=RESET_PIPELINE_LOGS_WORKER_ACTION, ui_state=app._current_ui_state())
    except Exception as exc:
        app._append_log(f"[ERROR] Pipeline log reset failed: {exc}")
        dialogs.show_error(str(exc))


def drain_queue(app) -> None:
    queue_scheduler.consume(app)
    _drain_worker_queue(app)
    _check_worker_lifecycle(app)
    if app._processing or app._worker_process is not None or app._worker_queue is not None:
        queue_scheduler.schedule(app)
    else:
        queue_scheduler.stop(app)


__all__ = [
    "_apply_artifact_tree_refs",
    "_artifact_tree_name",
    "_artifact_tree_parent",
    "_artifact_tree_refs",
    "_build_create_artifact_tree_request",
    "_build_create_database_request",
    "_check_worker_lifecycle",
    "_database_status_placeholder",
    "_drain_worker_queue",
    "_load_default_blueprints",
    "_load_release_preflight",
    "_release_label",
    "_resolve_activation_confirmation",
    "_safe_database_file_name",
    "_suggest_artifact_tree_dialog_values",
    "_target_database_path",
    "abort_processing",
    "activate_selected_release",
    "active_stage_name",
    "close_app",
    "create_artifact_tree",
    "create_database",
    "dialogs",
    "drain_queue",
    "finish_worker",
    "force_stop_worker",
    "mark_snapshot_aborted",
    "queue_scheduler",
    "refresh_database_status",
    "reset_logging_files",
    "reset_pipeline_logs",
    "reset_run_history",
    "start_processing",
    "start_worker",
    "wait_for_worker_exit",
]
