"""UiState field persistence for the Orchestrator UI."""

from __future__ import annotations

from ..models import UiState
from ..state import save_ui_state as persist_ui_state
from .types import EntryLike, UiFieldValues


def read_fields(app) -> UiFieldValues:
    semantic_release_mode = "database_default"
    if hasattr(app, "_semantic_release_mode_var"):
        raw_mode = app._semantic_release_mode_var.get().strip()
        semantic_release_mode = {
            "DB Release": "database_default",
            "Override Release": "override_selected",
        }.get(raw_mode, raw_mode.lower() or "database_default")
    return UiFieldValues(
        input_folder=app._input_entry.get().strip(),
        artifact_folder=app._artifact_entry.get().strip(),
        semantic_release_path=app._release_entry.get().strip(),
        corpus_output_folder=app._corpus_entry.get().strip(),
        selected_corpus_db_path=getattr(app, "_selected_db_entry", None).get().strip() if hasattr(app, "_selected_db_entry") else "",
        semantic_release_mode=semantic_release_mode,
        new_database_name=str(getattr(getattr(app, "_ui_state", None), "new_database_name", "") or "").strip(),
        new_database_bootstrap_mode=str(getattr(getattr(app, "_ui_state", None), "new_database_bootstrap_mode", "default_release") or "default_release").strip().lower() or "default_release",
        new_database_taxonomy_locale=str(getattr(getattr(app, "_ui_state", None), "new_database_taxonomy_locale", "") or "").strip().lower(),
        mode=app._mode_var.get().strip().lower() or "batch",
    )


def current_ui_state(app) -> UiState:
    return read_fields(app).to_ui_state()


def restore_ui_state(app) -> None:
    fields = UiFieldValues.from_ui_state(getattr(app, "_ui_state", UiState()))
    _with_suspended_events(app, lambda: _write_ui_fields(app, fields))


def save_ui_state(app) -> None:
    app._ui_state = current_ui_state(app)
    persist_ui_state(app._ui_state_path, app._ui_state)


def set_entry_path(app, entry: EntryLike, path: str) -> None:
    if not path:
        return
    _set_entry_text(entry, path)
    app._on_ui_change()


def _write_ui_fields(app, fields: UiFieldValues) -> None:
    _set_entry_text(app._input_entry, fields.input_folder)
    _set_entry_text(app._artifact_entry, fields.artifact_folder)
    _set_entry_text(app._release_entry, fields.semantic_release_path)
    _set_entry_text(app._corpus_entry, fields.corpus_output_folder)
    if hasattr(app, "_selected_db_entry"):
        _set_entry_text(app._selected_db_entry, fields.selected_corpus_db_path)
    if hasattr(app, "_semantic_release_mode_selector"):
        app._semantic_release_mode_selector.set("Override Release" if fields.semantic_release_mode == "override_selected" else "DB Release")
    app._mode_selector.set(fields.mode if fields.mode in {"batch", "single"} else "batch")


def _set_entry_text(entry: EntryLike, value: str) -> None:
    if hasattr(entry, "set"):
        entry.set(value)
        return
    entry.delete(0, "end")
    if value:
        entry.insert(0, value)


def _with_suspended_events(app, callback) -> None:
    app._suspend_surface_events = True
    try:
        callback()
    finally:
        app._suspend_surface_events = False
