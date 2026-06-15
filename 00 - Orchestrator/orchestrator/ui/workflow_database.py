"""Database creation workflow for Orchestrator UI actions."""

from __future__ import annotations

from pathlib import Path
import re

from ..pipeline import OrchestratorEngine
from . import dialogs, repository, validation
from .types import CREATE_DATABASE_WORKER_ACTION


def create_database(app) -> None:
    if app._processing:
        return
    app._flush_pending_saves()
    app._save_ui_state()
    fields = repository.read_fields(app)
    try:
        validation.ensure_create_database_ready(fields)
        blueprints, blueprint_error = _load_default_blueprints(app)
        dialog_result = dialogs.prompt_create_database(
            app,
            storage_folder=fields.corpus_output_folder,
            initial_name=fields.new_database_name,
            initial_bootstrap_mode=fields.new_database_bootstrap_mode,
            initial_taxonomy_locale=fields.new_database_taxonomy_locale,
            blueprints=blueprints,
            blueprint_error=blueprint_error,
        )
        if not dialog_result:
            return
        target_db_path = _target_database_path(fields.corpus_output_folder, dialog_result["database_name"])
        ui_state = fields.to_ui_state()
        ui_state.selected_corpus_db_path = str(target_db_path)
        ui_state.new_database_name = dialog_result["database_name"]
        ui_state.new_database_bootstrap_mode = dialog_result["bootstrap_mode"]
        ui_state.new_database_taxonomy_locale = dialog_result["taxonomy_locale"] or ui_state.new_database_taxonomy_locale
        ui_state.semantic_release_mode = "database_default"
        repository.set_entry_path(app, app._selected_db_entry, str(target_db_path))
        if hasattr(app, "_semantic_release_mode_selector"):
            app._semantic_release_mode_selector.set("DB Release")
        app._ui_state = ui_state
        app._save_ui_state()
        app._append_log(f"[DB] Creation started: {target_db_path}")
        app._start_worker(
            action=CREATE_DATABASE_WORKER_ACTION,
            ui_state=ui_state,
            worker_payload={"ui_state": ui_state.to_dict(), "create_database": _build_create_database_request(ui_state, dialog_result)},
        )
    except Exception as exc:
        app._append_log(f"[ERROR] Database creation failed: {exc}")
        dialogs.show_error(str(exc))


def _build_create_database_request(ui_state, dialog_result: dict[str, str]) -> dict[str, str]:
    target_db_path = _target_database_path(ui_state.corpus_output_folder, dialog_result["database_name"])
    return {
        "database_name": dialog_result["database_name"],
        "target_db_path": str(target_db_path),
        "bootstrap_mode": dialog_result["bootstrap_mode"],
        "blueprint_ref": "default" if dialog_result["bootstrap_mode"] == "default_release" else "",
        "taxonomy_locale": dialog_result.get("taxonomy_locale", ""),
    }


def _load_default_blueprints(app) -> tuple[list[dict[str, object]], str]:
    engine = OrchestratorEngine(orchestrator_root=app._project_root)
    try:
        blueprints = engine.list_default_blueprints()
    except Exception as exc:
        return [], str(exc)
    finally:
        engine.close()
    return [dict(item) for item in blueprints], ""


def _target_database_path(storage_folder: str, database_name: str) -> Path:
    storage_path = Path(str(storage_folder or "").strip())
    if not str(storage_path).strip():
        raise ValueError("Database Storage Folder is not set.")
    return storage_path / _safe_database_file_name(database_name)


def _safe_database_file_name(database_name: str) -> str:
    raw_name = str(database_name or "").strip()
    if not raw_name:
        raise ValueError("Database name must not be empty.")
    stem = raw_name[:-3] if raw_name.lower().endswith(".db") else raw_name
    safe_stem = re.sub(r'[<>:"/\\\\|?*]+', "-", stem).strip().strip(".")
    if not safe_stem:
        raise ValueError("Database name contains no valid characters.")
    return f"{safe_stem}.db"
