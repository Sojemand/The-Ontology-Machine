"""Projection controller for the Semantic Release editor."""

from __future__ import annotations

import copy
from typing import Any

import customtkinter as ctk

from . import theme
from .taxonomy_release_editor_projection_pickers import (
    _picker_options,
    _projection_selection,
    _refresh_projection_pickers,
)
from .taxonomy_release_editor_taxonomy import _sync_current_taxonomy_item
from .taxonomy_release_editor_widgets import _replace_entry, _replace_text, _textbox_value
from .taxonomy_release_model import (
    PROJECTION_LIST_FIELDS,
    _csv,
    _projections,
    _release,
)


def _refresh_projection_list(frame) -> None:
    for child in frame._projection_list.winfo_children():
        child.destroy()
    projections = _projections(frame)
    if projections and not frame._selected_projection_id:
        frame._selected_projection_id = str(projections[0].get("projection_id") or "")
    for row, projection in enumerate(projections):
        projection_id = str(projection.get("projection_id") or "")
        label = str(projection.get("label") or projection_id or "(new)")
        border = 1 if projection_id == frame._selected_projection_id else 0
        ctk.CTkButton(
            frame._projection_list,
            text=f"{label}\n{projection_id}",
            anchor="w",
            border_width=border,
            command=lambda pid=projection_id, target=frame: _show_projection(target, pid),
        ).grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=3, sticky="we")


def _show_projection(frame, projection_id: str) -> None:
    _sync_current_taxonomy_item(frame)
    if projection_id and projection_id != frame._selected_projection_id:
        _sync_current_projection(frame)
    projections = _projections(frame)
    projection = next((item for item in projections if str(item.get("projection_id") or "") == projection_id), projections[0] if projections else {})
    frame._selected_projection_id = str(projection.get("projection_id") or "")
    routing = projection.get("routing") if isinstance(projection.get("routing"), dict) else {}
    signals = routing.get("surface_signals") if isinstance(routing.get("surface_signals"), dict) else {}
    _refresh_projection_pickers(frame, projection)
    values = {
        "projection_id": projection.get("projection_id", ""),
        "label": projection.get("label", ""),
        "description": projection.get("description", ""),
        "when_to_use": routing.get("when_to_use", ""),
        "avoid_when": routing.get("avoid_when", ""),
        "text_markers": ", ".join(str(value) for value in signals.get("text_markers", []) or []),
    }
    for name, widget in frame._projection_widgets.items():
        if isinstance(widget, ctk.CTkTextbox):
            _replace_text(widget, values.get(name, ""))
        else:
            _replace_entry(widget, values.get(name, ""))
    _refresh_projection_list(frame)


def _update_projection_choices(frame) -> None:
    _sync_current_taxonomy_item(frame)
    _sync_current_projection(frame)
    projection = next((item for item in _projections(frame) if str(item.get("projection_id") or "") == frame._selected_projection_id), {})
    _refresh_projection_pickers(frame, projection)


def _sync_current_projection(frame) -> None:
    projections = _projections(frame)
    if not projections or not frame._selected_projection_id:
        return
    projection = next((item for item in projections if str(item.get("projection_id") or "") == frame._selected_projection_id), None)
    if projection is None:
        return
    old_id = str(projection.get("projection_id") or "")
    projection["projection_id"] = frame._projection_widgets["projection_id"].get().strip() or old_id
    projection["label"] = frame._projection_widgets["label"].get().strip()
    projection["description"] = frame._projection_widgets["description"].get().strip()
    for field_name in PROJECTION_LIST_FIELDS:
        projection[field_name] = _projection_selection(frame, field_name)
    routing = projection.setdefault("routing", {})
    if not isinstance(routing, dict):
        routing = {}
        projection["routing"] = routing
    routing["when_to_use"] = _textbox_value(frame._projection_widgets["when_to_use"])
    routing["avoid_when"] = _textbox_value(frame._projection_widgets["avoid_when"])
    routing["example_document_types"] = _projection_selection(frame, "example_document_types")
    routing["section_roles"] = _projection_selection(frame, "section_roles")
    routing["party_roles"] = _projection_selection(frame, "party_roles")
    signals = routing.setdefault("surface_signals", {})
    if not isinstance(signals, dict):
        signals = {}
        routing["surface_signals"] = signals
    signals["text_markers"] = _csv(_textbox_value(frame._projection_widgets["text_markers"]))
    signals["section_roles"] = list(routing["section_roles"])
    signals["party_roles"] = list(routing["party_roles"])
    signals.setdefault("domain_markers", {})
    frame._selected_projection_id = str(projection["projection_id"])


def _new_projection(frame) -> None:
    _sync_current_projection(frame)
    release = _release(frame)
    projections = release.setdefault("projections", [])
    projection_id = f"draft.projection.{len(projections) + 1}.v1"
    projections.append(
        {
            "projection_id": projection_id,
            "label": "Draft Projection",
            "description": "",
            "domain_ids": [],
            "include_document_types": [],
            "include_categories": [],
            "include_subcategories": [],
            "include_field_codes": [],
            "include_row_types": [],
            "include_cell_codes": [],
            "promotion_rules": [],
            "routing": {
                "when_to_use": "",
                "avoid_when": "",
                "example_document_types": [],
                "section_roles": [],
                "party_roles": [],
                "surface_signals": {"text_markers": [], "domain_markers": {}, "section_roles": [], "party_roles": []},
            },
        }
    )
    frame._selected_projection_id = projection_id
    _refresh_projection_list(frame)
    _show_projection(frame, projection_id)


def _duplicate_projection(frame) -> None:
    _sync_current_projection(frame)
    projection = next((item for item in _projections(frame) if str(item.get("projection_id") or "") == frame._selected_projection_id), None)
    if projection is None:
        return
    payload = copy.deepcopy(projection)
    payload["projection_id"] = f"{projection.get('projection_id')}.copy"
    payload["label"] = f"{projection.get('label') or projection.get('projection_id')} Copy"
    _projections(frame).append(payload)
    frame._selected_projection_id = str(payload["projection_id"])
    _refresh_projection_list(frame)
    _show_projection(frame, frame._selected_projection_id)


def _delete_projection(frame) -> None:
    projections = _projections(frame)
    for index, item in enumerate(projections):
        if str(item.get("projection_id") or "") == frame._selected_projection_id:
            del projections[index]
            break
    frame._selected_projection_id = str(projections[0].get("projection_id") or "") if projections else ""
    _refresh_projection_list(frame)
    _show_projection(frame, frame._selected_projection_id)
