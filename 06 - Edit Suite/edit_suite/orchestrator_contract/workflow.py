"""Workflow helpers for Edit Suite contract actions."""

from __future__ import annotations


def error_response(message: str) -> dict:
    return {"status": "error", "reason": str(message)}


def healthcheck(*, ensure_startup_prerequisites, discover_registry) -> dict:
    try:
        context = ensure_startup_prerequisites()
        snapshot = discover_registry(context.pipeline_root, probe_contracts=False)
    except Exception as exc:
        return {"status": "error", "healthy": False, "message": str(exc), "dependencies": []}
    return {"status": "ok", "healthy": True, "message": "", "dependencies": [], "module_count": len(snapshot.entries)}
