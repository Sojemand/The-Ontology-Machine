"""Worker-runtime helpers for orchestrator UI workflow actions."""

from __future__ import annotations

import queue

from ..models import PipelineSnapshot, STAGE_NAMES, StageSnapshot
from ..worker import run_worker_process, terminate_process_tree
from . import dialogs, queue_scheduler, worker_runtime
from .types import ACTIVATE_RELEASE_WORKER_ACTION, CREATE_DATABASE_WORKER_ACTION, RESET_PIPELINE_LOGS_WORKER_ACTION, RESET_WORKER_ACTION, RUN_WORKER_ACTION, WorkerResources


def start_worker(app, *, action, ui_state, worker_payload=None) -> None:
    app._cleanup_worker_resources()
    app._processing = True
    app._stop_requested = False
    app._active_action = action
    app._snapshot = PipelineSnapshot(is_running=True)
    app._apply_snapshot(app._snapshot)
    resources = WorkerResources()
    try:
        resources.queue = app._mp_context.Queue()
        resources.cancel_event = app._mp_context.Event()
        resources.process = app._mp_context.Process(
            target=run_worker_process,
            args=(
                str(app._project_root),
                action,
                worker_payload if isinstance(worker_payload, dict) else ui_state.to_dict(),
                resources.queue,
                resources.cancel_event,
            ),
            daemon=True,
        )
        resources.process.start()
    except Exception:
        worker_runtime.rollback_worker_bootstrap(app, resources)
        raise
    app._worker_queue = resources.queue
    app._worker_cancel_event = resources.cancel_event
    app._worker_process = resources.process
    app._start_btn.configure(text="Processing..." if action == RUN_WORKER_ACTION else "Process")
    if hasattr(app, "_activate_release_btn"):
        app._activate_release_btn.configure(text="Activate..." if action == ACTIVATE_RELEASE_WORKER_ACTION else "Activate")
    if hasattr(app, "_create_database_btn"):
        app._create_database_btn.configure(text="Create..." if action == CREATE_DATABASE_WORKER_ACTION else "Create Database")
    app._reset_btn.configure(text="Reset Error Bundle..." if action == RESET_WORKER_ACTION else "Reset Error Bundle")
    if hasattr(app, "_reset_pipeline_logs_btn"):
        app._reset_pipeline_logs_btn.configure(
            state="disabled",
            text="Reset Pipeline Logs..." if action == RESET_PIPELINE_LOGS_WORKER_ACTION else "Reset Pipeline Logs",
        )
    app._abort_btn.configure(text="Abort")
    app._update_button_state()
    queue_scheduler.schedule(app)


def abort_processing(app) -> None:
    if not app._processing or app._worker_process is None or app._stop_requested:
        return
    app._stop_requested = True
    if app._worker_cancel_event is not None:
        app._worker_cancel_event.set()
    app._abort_btn.configure(state="disabled", text="Aborting...")
    app._append_log("[ABORT] Stop requested")
    app.after(300, app._force_stop_worker)


def force_stop_worker(app) -> None:
    if not app._stop_requested or app._worker_process is None or not app._worker_process.is_alive():
        return
    terminate_process_tree(app._worker_process.pid)
    app.after(200, app._force_stop_worker)


def drain_queue(app) -> None:
    queue_scheduler.consume(app)
    _drain_worker_queue(app)
    _check_worker_lifecycle(app)
    if app._processing or app._worker_process is not None or app._worker_queue is not None:
        queue_scheduler.schedule(app)
    else:
        queue_scheduler.stop(app)


def finish_worker(app, *, cancelled: bool = False, error: str | None = None) -> None:
    if app._worker_process is None and not app._processing:
        return
    previous_action = getattr(app, "_active_action", "")
    app._processing = False
    app._snapshot.is_running = False
    if cancelled:
        mark_snapshot_aborted(app)
        app._append_log("[ABORT] Processing stopped")
    else:
        app._snapshot.aborted = False
    app._stop_requested = False
    app._active_action = ""
    app._start_btn.configure(text="Process")
    if hasattr(app, "_activate_release_btn"):
        app._activate_release_btn.configure(text="Activate")
    if hasattr(app, "_create_database_btn"):
        app._create_database_btn.configure(text="Create Database")
    app._reset_btn.configure(text="Reset Error Bundle")
    if hasattr(app, "_reset_pipeline_logs_btn"):
        app._reset_pipeline_logs_btn.configure(state="normal", text="Reset Pipeline Logs")
    app._abort_btn.configure(text="Abort")
    queue_scheduler.stop(app)
    wait_for_worker_exit(app)
    app._cleanup_worker_resources()
    app._apply_snapshot(app._snapshot)
    app._update_button_state()
    if hasattr(app, "_refresh_database_status") and action_requires_database_refresh(previous_action):
        app._refresh_database_status()
    if error:
        dialogs.show_error(error)


def mark_snapshot_aborted(app) -> None:
    app._snapshot.aborted = True
    stage_name = active_stage_name(app)
    if not stage_name:
        return
    current = app._snapshot.stage_statuses.get(stage_name, StageSnapshot())
    detail = current.detail or app._snapshot.current_file
    app._snapshot.stage_statuses[stage_name] = StageSnapshot(
        status="Aborted",
        detail=detail,
        progress_current=current.progress_current,
        progress_total=current.progress_total,
        progress_label=current.progress_label,
    )


def active_stage_name(app) -> str | None:
    for name in STAGE_NAMES:
        current = app._snapshot.stage_statuses.get(name, StageSnapshot())
        if current.status == "Processing...":
            return name
    if app._active_action == RUN_WORKER_ACTION:
        return "Intake"
    if app._active_action in {ACTIVATE_RELEASE_WORKER_ACTION, CREATE_DATABASE_WORKER_ACTION}:
        return "Corpus Builder"
    return None


def action_requires_database_refresh(action: str) -> bool:
    return action in {RUN_WORKER_ACTION, ACTIVATE_RELEASE_WORKER_ACTION, CREATE_DATABASE_WORKER_ACTION}


def wait_for_worker_exit(app, timeout: float = 0.5) -> None:
    worker_runtime.wait_for_worker_exit(app, timeout=timeout)


def close_app(app) -> None:
    worker_runtime.close_app(app)


def _drain_worker_queue(app) -> None:
    while app._worker_queue is not None:
        try:
            kind, payload = app._worker_queue.get_nowait()
        except queue.Empty:
            break
        except (EOFError, OSError, ValueError):
            break
        if kind == "snapshot":
            app._snapshot = payload
            app._apply_snapshot(app._snapshot)
        elif kind == "log":
            app._append_log(str(payload))
        elif kind == "done":
            app._finish_worker()
        elif kind == "cancelled":
            app._finish_worker(cancelled=True)
        elif kind == "error":
            app._finish_worker(error=str(payload))


def _check_worker_lifecycle(app) -> None:
    if app._worker_process is None or not app._processing or app._worker_process.is_alive():
        return
    exitcode = app._worker_process.exitcode
    if app._stop_requested:
        app._finish_worker(cancelled=True)
    elif exitcode not in (0, None):
        app._finish_worker(error=f"Worker process ended unexpectedly (exit code {exitcode}).")
    else:
        app._finish_worker()
