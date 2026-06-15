"""Queue drain scheduling for the orchestrator worker loop."""

from __future__ import annotations

POLL_INTERVAL_MS = 50


def schedule(app) -> None:
    if getattr(app, "_queue_poll_handle", None) is not None or not hasattr(app, "after"):
        return
    app._queue_poll_handle = app.after(POLL_INTERVAL_MS, app._drain_queue)


def consume(app) -> None:
    app._queue_poll_handle = None


def stop(app) -> None:
    handle = getattr(app, "_queue_poll_handle", None)
    if handle is not None and hasattr(app, "after_cancel"):
        try:
            app.after_cancel(handle)
        except Exception:
            pass
    app._queue_poll_handle = None
