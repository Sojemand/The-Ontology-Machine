"""Structured editor for compiled Semantic Release taxonomy/projection drafts."""
from __future__ import annotations

import copy
from tkinter import filedialog as fd
from typing import Any

import customtkinter as ctk

from . import background_jobs, theme
from . import taxonomy_release_editor_layout as editor_layout
from . import taxonomy_release_editor_projection as projection_controller
from .taxonomy_release_editor_projection import (
    _delete_projection,
    _duplicate_projection,
    _new_projection,
    _refresh_projection_list,
    _sync_current_projection,
)
from .taxonomy_release_editor_refresh import _refresh_candidates, _refresh_summary, _refresh_verify
from .taxonomy_release_editor_taxonomy import (
    _delete_taxonomy_item,
    _duplicate_taxonomy_item,
    _new_taxonomy_item,
    _refresh_taxonomy_list,
    _select_taxonomy_item,
    _select_taxonomy_section,
    _show_taxonomy_item,
    _sync_current_taxonomy_item,
)
from .taxonomy_release_editor_widgets import _replace_entry
from .taxonomy_release_model import (
    SCHEMA_VERSION,
    TAXONOMY_SECTIONS,
    _default_working_release_path,
    _normalize_draft,
    _projections,
    _read_release,
    _require_release_shape,
    _scan_release_candidates,
    _taxonomy_items,
)


def render(parent, surface, *, app):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    frame._app = app
    frame._surface_id = surface.surface_id
    frame._draft = _normalize_draft(surface.draft)
    frame._candidate_labels = {}
    frame._taxonomy_section = ctk.StringVar(value=TAXONOMY_SECTIONS[0])
    frame._selected_taxonomy_index = 0
    frame._selected_projection_id = ""
    editor_layout.render_source_controls(frame, _layout_actions())
    editor_layout.render_release_summary(frame)
    editor_layout.render_tabs(frame, _layout_actions())
    _refresh_all(frame)
    return frame


def read_value(widget) -> dict:
    _sync_current_taxonomy_item(widget)
    _sync_current_projection(widget)
    widget._draft["artifact_root"] = widget._artifact_root_entry.get().strip()
    widget._draft["selected_release_path"] = _selected_release_path(widget)
    widget._draft["working_release_path"] = widget._working_release_entry.get().strip()
    widget._draft["corpus_db_path"] = widget._corpus_db_entry.get().strip()
    return copy.deepcopy(widget._draft)


def _layout_actions() -> dict[str, Any]:
    return {
        "browse_artifact_root": _browse_artifact_root,
        "scan_artifact_root": _scan_artifact_root,
        "load_selected_release": _load_selected_release,
        "browse_corpus_db": _browse_corpus_db,
        "select_taxonomy_section": _select_taxonomy_section,
        "new_taxonomy_item": _new_taxonomy_item,
        "duplicate_taxonomy_item": _duplicate_taxonomy_item,
        "delete_taxonomy_item": _delete_taxonomy_item,
        "new_projection": _new_projection,
        "duplicate_projection": _duplicate_projection,
        "delete_projection": _delete_projection,
        "update_projection_choices": _update_projection_choices,
        "trigger_verify": _trigger_verify,
    }


def _browse_artifact_root(frame) -> None:
    selected = fd.askdirectory(title="Select Artifact Tree")
    if not selected:
        return
    _replace_entry(frame._artifact_root_entry, selected)
    _scan_artifact_root(frame)


def _browse_corpus_db(frame) -> None:
    selected = fd.askopenfilename(title="Select Corpus DB", filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")])
    if not selected:
        return
    _replace_entry(frame._corpus_db_entry, selected)


def _scan_artifact_root(frame) -> None:
    root = frame._artifact_root_entry.get().strip()
    frame._draft["artifact_root"] = root
    frame._draft["release_candidates"] = []
    frame._draft["selected_release_path"] = ""
    frame._draft["verification"] = {"status": "scan_running", "issues": [], "warnings": ["Scanning Artifact Tree in the background."]}
    _refresh_candidates(frame)
    _refresh_verify(frame)
    token = background_jobs.next_token(frame, "taxonomy_release_scan")
    background_jobs.start(
        frame,
        work=lambda: _scan_release_candidates(root),
        deliver=lambda result, error: _finish_scan_artifact_root(frame, token, root, result, error),
    )


def _finish_scan_artifact_root(frame, token: int, root: str, result, error: Exception | None) -> None:
    if not background_jobs.is_current(frame, "taxonomy_release_scan", token):
        return
    if error is not None:
        frame._draft["release_candidates"] = []
        frame._draft["selected_release_path"] = ""
        frame._draft["verification"] = {"status": "scan_error", "issues": [str(error)], "warnings": []}
        _refresh_all(frame)
        return
    candidates = result if isinstance(result, list) else []
    frame._draft["artifact_root"] = root
    frame._draft["release_candidates"] = candidates
    if candidates:
        frame._draft["selected_release_path"] = candidates[0]["path"]
        frame._draft["verification"] = {"status": "scan_complete", "issues": [], "warnings": []}
    else:
        frame._draft["selected_release_path"] = ""
        frame._draft["verification"] = {"status": "scan_complete", "issues": [], "warnings": ["No complete Semantic Release found."]}
    _refresh_candidates(frame)
    _refresh_verify(frame)


def _load_selected_release(frame) -> None:
    path = _selected_release_path(frame)
    if not path:
        frame._draft["verification"] = {"status": "load_error", "issues": ["No Semantic Release selected."], "warnings": []}
        _refresh_summary(frame)
        _refresh_verify(frame)
        return
    try:
        release = _read_release(path)
        _require_release_shape(release)
    except Exception as exc:
        frame._draft["verification"] = {"status": "load_error", "issues": [str(exc)], "warnings": []}
        _refresh_summary(frame)
        _refresh_verify(frame)
        return
    artifact_root = frame._artifact_root_entry.get().strip()
    frame._draft.update(
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_root": artifact_root,
            "selected_release_path": path,
            "working_release_path": _default_working_release_path(artifact_root, release),
            "origin": {
                "artifact_root": artifact_root,
                "release_path": path,
                "release_id": str(release.get("release_id") or ""),
                "release_version": str(release.get("release_version") or ""),
                "fingerprint": str(release.get("fingerprint") or ""),
                "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
                "master_core_signature": "",
            },
            "release": release,
            "verification": {"status": "draft_loaded", "issues": [], "warnings": ["Run Verify before applying this release."]},
        }
    )
    _replace_entry(frame._working_release_entry, frame._draft["working_release_path"])
    _refresh_all(frame)


def _trigger_verify(frame) -> None:
    app = getattr(frame, "_app", None)
    if app is not None and hasattr(app, "validate_surface"):
        app.validate_surface(frame._surface_id)


def _refresh_all(frame) -> None:
    _refresh_candidates(frame)
    _refresh_summary(frame)
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)
    _refresh_projection_list(frame)
    _show_projection(frame, frame._selected_projection_id)
    _refresh_verify(frame)


def _show_projection(frame, projection_id: str) -> None:
    projection_controller._show_projection(frame, projection_id)


def _refresh_projection_pickers(frame, projection: dict[str, Any]) -> None:
    projection_controller._refresh_projection_pickers(frame, projection)


def _picker_options(frame, field_name: str) -> list[tuple[str, str]]:
    return projection_controller._picker_options(frame, field_name)


def _update_projection_choices(frame) -> None:
    _sync_current_taxonomy_item(frame)
    _sync_current_projection(frame)
    projection = next((item for item in _projections(frame) if str(item.get("projection_id") or "") == frame._selected_projection_id), {})
    _refresh_projection_pickers(frame, projection)


def _selected_release_path(frame) -> str:
    label = frame._candidate_var.get()
    return str(frame._candidate_labels.get(label) or frame._draft.get("selected_release_path") or "")
