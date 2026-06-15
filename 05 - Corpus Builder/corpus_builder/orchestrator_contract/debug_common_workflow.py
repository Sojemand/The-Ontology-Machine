"""Shared debug workflow response helpers."""

from __future__ import annotations

from pathlib import Path

from ..models import LoadBatchResult
from . import debug_support


def result_status(batch: LoadBatchResult, *, cancelled: bool) -> str:
    if cancelled:
        return "cancelled"
    return "error" if batch.errors else "ok"


def summary_text(batch: LoadBatchResult, *, cancelled: bool) -> str:
    if cancelled:
        return f"Abgebrochen nach {len(batch.results)} Artefakten"
    return f"{batch.loaded} geladen, {batch.skipped} uebersprungen, {batch.archived} archiviert, {batch.errors} Fehler"


def result_row(item) -> dict[str, str]:
    return {
        "status": str(item.status or ""),
        "document_id": str(item.document_id or ""),
        "reason": str(item.reason or ""),
    }


def release_meta(release: dict, active_release_path: Path, replaced_existing: bool) -> dict[str, object]:
    return {
        "active_release_id": release.get("release_id"),
        "active_release_version": release.get("release_version"),
        "active_release_path": str(active_release_path),
        "replaced_existing": replaced_existing,
    }


def cancelled(session_root: Path, *, summary: str) -> dict:
    debug_support.write_snapshot(session_root, status="cancelled", detail=summary)
    debug_support.append_log(session_root, f"[CANCELLED] {summary}")
    return debug_support.write_result(session_root, {"status": "cancelled", "summary": summary})


def error(payload: dict, *, summary: str, message: str) -> dict:
    session_root = payload.get("session_root")
    if not isinstance(session_root, str) or not session_root.strip():
        return {"status": "error", "summary": summary, "error": message}
    root = Path(session_root)
    debug_support.append_log(root, f"[ERROR] {message}")
    debug_support.write_snapshot(root, status="error", detail=message)
    return debug_support.write_result(root, {"status": "error", "summary": summary, "error": message})
