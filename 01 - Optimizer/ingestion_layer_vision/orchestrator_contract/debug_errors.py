"""Debug-action error handling for optimizer contract workflows."""
from __future__ import annotations

from . import debug_support, validation


def run_debug_action(payload: dict, action, *, summary: str) -> dict:
    try:
        return action()
    except Exception as exc:
        return debug_error(payload, summary=summary, message=str(exc))


def debug_error(payload: dict, *, summary: str, message: str) -> dict:
    try:
        session_root = validation.require_session_root(payload)
    except Exception:
        return {"status": "error", "error": message}
    if debug_support.cancel_requested(session_root):
        debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
        return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})
    debug_support.append_log(session_root, f"[ERROR] {message}")
    debug_support.write_snapshot(session_root, status="error", detail=message)
    return debug_support.write_result(session_root, {"status": "error", "summary": summary, "error": message})
