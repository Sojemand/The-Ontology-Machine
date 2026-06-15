"""Database status refresh workflow for Orchestrator UI actions."""

from __future__ import annotations

from pathlib import Path

from ..pipeline import OrchestratorEngine
from . import repository


def refresh_database_status(app) -> None:
    status = _database_status_placeholder()
    try:
        fields = repository.read_fields(app)
        ui_state = fields.to_ui_state()
        selected_text = str(ui_state.selected_corpus_db_path or "").strip()
        status["selected_database"] = selected_text or "-"
        if not selected_text:
            status["db_state"] = "No database selected"
            _apply_database_status(app, status)
            return
        selected_db_path = Path(selected_text)
        if not selected_db_path.exists():
            status["db_state"] = "Not created yet"
            _apply_database_status(app, status)
            return
        detail = _semantic_status(app, ui_state, selected_db_path)
        runtime_truth_source = str(detail.get("runtime_truth_source") or "").strip()
        if runtime_truth_source == "db_snapshot" and str(detail.get("active_snapshot_id") or "").strip():
            total_documents = int(detail.get("total_documents") or 0)
            stale_documents = int(detail.get("stale_documents") or 0)
            stale_suffix = f" | stale {stale_documents}" if stale_documents else ""
            status["db_state"] = f"Ready | {total_documents} documents{stale_suffix}"
            status["active_release"] = _release_label(detail.get("active_release_id"), detail.get("active_release_version"))
        elif runtime_truth_source in {"filesystem_release", "uninitialized", "snapshot_missing"}:
            status["db_state"] = "No active DB semantics"
            status["active_release"] = "-"
        else:
            status["db_state"] = runtime_truth_source or "Status unknown"
    except Exception as exc:
        status["db_state"] = f"Status error: {exc}"
    _apply_database_status(app, status)


def _semantic_status(app, ui_state, selected_db_path: Path) -> dict:
    engine = OrchestratorEngine(orchestrator_root=app._project_root)
    try:
        return engine.semantic_status(ui_state, corpus_db_path=selected_db_path)
    finally:
        engine.close()


def _apply_database_status(app, status: dict[str, str]) -> None:
    app._database_status = status
    app._apply_snapshot(app._snapshot)


def _database_status_placeholder() -> dict[str, str]:
    return {
        "selected_database": "-",
        "db_state": "Not loaded yet",
        "active_release": "-",
    }


def _release_label(release_id, release_version) -> str:
    release_text = str(release_id or "").strip()
    version_text = str(release_version or "").strip()
    if release_text and version_text:
        return f"{release_text} | {version_text}"
    return release_text or "-"
