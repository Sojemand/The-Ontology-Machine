"""Worker runtime helpers for shutdown, cleanup and bootstrap rollback."""
from __future__ import annotations

from ..worker import terminate_process_tree
from . import queue_scheduler
from .types import WorkerResources


def cleanup_worker_resources(app) -> None:
    if app._worker_process is not None:
        if not app._worker_process.is_alive():
            try:
                app._worker_process.join(timeout=0.1)
            except Exception:
                pass
            try:
                app._worker_process.close()
            except Exception:
                pass
        app._worker_process = None
    if app._worker_queue is not None:
        try:
            app._worker_queue.close()
        except Exception:
            pass
        try:
            app._worker_queue.join_thread()
        except Exception:
            pass
        app._worker_queue = None
    app._worker_cancel_event = None


def wait_for_worker_exit(app, timeout: float = 0.5) -> None:
    if app._worker_process is None:
        return
    try:
        app._worker_process.join(timeout=timeout)
    except Exception:
        return


def close_app(app) -> None:
    app._save_ui_state()
    queue_scheduler.stop(app)
    if app._worker_process is not None and app._worker_process.is_alive():
        terminate_process_tree(app._worker_process.pid)
        app._wait_for_worker_exit(timeout=1.0)
    app._cleanup_worker_resources()
    app.destroy()


def rollback_worker_bootstrap(app, resources: WorkerResources) -> None:
    app._processing = False
    app._stop_requested = False
    app._active_action = ""
    app._snapshot.is_running = False
    app._snapshot.aborted = False
    try:
        if resources.process is not None:
            resources.process.close()
    except Exception:
        pass
    if resources.queue is not None:
        try:
            resources.queue.close()
        except Exception:
            pass
        try:
            resources.queue.join_thread()
        except Exception:
            pass
    app._worker_process = None
    app._worker_queue = None
    app._worker_cancel_event = None
    app._apply_snapshot(app._snapshot)
    app._update_button_state()
