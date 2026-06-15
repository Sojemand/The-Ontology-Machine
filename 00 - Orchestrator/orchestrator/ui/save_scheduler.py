"""Debounced save scheduling for UI-owned state files."""

from __future__ import annotations

SAVE_DELAY_MS = 250


def configure(app) -> None:
    if hasattr(app, "_pending_save_jobs"):
        return
    app._pending_save_jobs = {}


def schedule(app, key: str, callback, *, delay_ms: int = SAVE_DELAY_MS) -> None:
    configure(app)
    job = app._pending_save_jobs.get(key, {})
    job["callback"] = callback
    job["dirty"] = True
    _cancel_handle(app, job.get("handle"))
    if hasattr(app, "after"):
        job["handle"] = app.after(delay_ms, lambda save_key=key: _run(app, save_key))
    else:
        job["handle"] = None
        _run(app, key)
    app._pending_save_jobs[key] = job


def flush(app, key: str):
    configure(app)
    job = app._pending_save_jobs.get(key)
    if not isinstance(job, dict) or not job.get("dirty"):
        return None
    _cancel_handle(app, job.get("handle"))
    job["handle"] = None
    app._pending_save_jobs[key] = job
    return _invoke(app, key)


def flush_all(app) -> None:
    configure(app)
    for key in tuple(app._pending_save_jobs):
        flush(app, key)


def cancel(app, key: str) -> None:
    configure(app)
    job = app._pending_save_jobs.get(key)
    if not isinstance(job, dict):
        return
    _cancel_handle(app, job.get("handle"))
    job["handle"] = None
    job["dirty"] = False
    app._pending_save_jobs[key] = job


def _run(app, key: str) -> None:
    configure(app)
    job = app._pending_save_jobs.get(key)
    if not isinstance(job, dict):
        return
    job["handle"] = None
    app._pending_save_jobs[key] = job
    if job.get("dirty"):
        _invoke(app, key)


def _invoke(app, key: str):
    job = app._pending_save_jobs.get(key, {})
    callback = job.get("callback")
    job["dirty"] = False
    app._pending_save_jobs[key] = job
    if callable(callback):
        return callback()
    return None


def _cancel_handle(app, handle) -> None:
    if handle is None or not hasattr(app, "after_cancel"):
        return
    try:
        app.after_cancel(handle)
    except Exception:
        return
