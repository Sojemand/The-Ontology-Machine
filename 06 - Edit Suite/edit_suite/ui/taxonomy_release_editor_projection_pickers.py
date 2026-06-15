"""Picker helpers for Semantic Release projection editing."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from . import theme
from .taxonomy_release_editor_widgets import _textbox_value
from .taxonomy_release_model import (
    PROJECTION_LIST_FIELDS,
    PROJECTION_TAXONOMY_FIELDS,
    SECTION_ROLE_OPTIONS,
    _csv,
    _item_key,
    _release,
    _text_values,
    _truthy_var,
)


def _refresh_projection_pickers(frame, projection: dict[str, Any]) -> None:
    pickers = getattr(frame, "_projection_pickers", {})
    if not isinstance(pickers, dict):
        return
    routing = projection.get("routing") if isinstance(projection.get("routing"), dict) else {}
    signals = routing.get("surface_signals") if isinstance(routing.get("surface_signals"), dict) else {}
    selected = {field_name: _text_values(projection.get(field_name)) for field_name in PROJECTION_LIST_FIELDS}
    selected["example_document_types"] = _text_values(routing.get("example_document_types"))
    selected["section_roles"] = _text_values(signals.get("section_roles") or routing.get("section_roles"))
    selected["party_roles"] = _text_values(signals.get("party_roles") or routing.get("party_roles"))
    for field_name, picker in pickers.items():
        _set_picker_options(picker, _picker_options(frame, field_name), selected.get(field_name, []))


def _set_picker_options(picker: dict[str, Any], options: list[tuple[str, str]], selected_values: list[str]) -> None:
    container = picker.get("container")
    selected = set(_text_values(selected_values))
    picker["options"] = [value for value, _label in options]
    picker["vars"] = {}
    if container is None:
        return
    for child in container.winfo_children():
        child.destroy()
    for row, (value, label) in enumerate(options):
        variable = ctk.BooleanVar(value=value in selected)
        picker["vars"][value] = variable
        ctk.CTkCheckBox(container, text=label, variable=variable, font=theme.font_small()).grid(
            row=row,
            column=0,
            padx=theme.PADDING_SMALL,
            pady=2,
            sticky="w",
        )


def _picker_options(frame, field_name: str) -> list[tuple[str, str]]:
    if field_name == "section_roles":
        return [(value, value) for value in SECTION_ROLE_OPTIONS]
    section = PROJECTION_TAXONOMY_FIELDS.get(field_name)
    if section:
        return _taxonomy_options(frame, section)
    return []


def _projection_selection(frame, field_name: str) -> list[str]:
    picker = getattr(frame, "_projection_pickers", {}).get(field_name) if isinstance(getattr(frame, "_projection_pickers", {}), dict) else None
    if isinstance(picker, dict):
        variables = picker.get("vars")
        if isinstance(variables, dict):
            return [str(value) for value, variable in variables.items() if _truthy_var(variable)]
    widget = getattr(frame, "_projection_widgets", {}).get(field_name) if isinstance(getattr(frame, "_projection_widgets", {}), dict) else None
    if widget is None:
        return []
    if isinstance(widget, ctk.CTkTextbox):
        return _csv(_textbox_value(widget))
    try:
        return _csv(widget.get())
    except TypeError:
        return _csv(_textbox_value(widget))


def _taxonomy_options(frame, section: str) -> list[tuple[str, str]]:
    master = _release(frame).get("master_taxonomy")
    if not isinstance(master, dict):
        return []
    items = master.get(section)
    if not isinstance(items, list):
        return []
    options: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = _item_key(item)
        if not value:
            continue
        label = str(item.get("label") or item.get("description") or value).strip()
        display = f"{label} ({value})" if label and label != value else value
        options.append((value, display))
    return options
