"""Hybrid editor for nested top-level policy surfaces."""
from __future__ import annotations

import json

import customtkinter as ctk

from . import theme
from .text_widgets import create_json_textbox, create_readonly_text

_JSON_HEIGHT = 176
_LIST_HEIGHT = 112


def render(parent, surface, *, width: int):
    del width
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    specs: dict[str, dict] = {}
    frame._field_order = list(surface.draft)
    row = 0
    for label, field_names in grouped_fields(surface):
        group = ctk.CTkFrame(frame)
        group.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
        group.grid_columnconfigure(0, weight=1)
        inner_row = 0
        if label:
            create_readonly_text(
                group,
                text=label,
                font=theme.font_header(),
                min_lines=1,
                max_lines=1,
                height=theme.INPUT_HEIGHT,
            ).grid(row=inner_row, column=0, padx=theme.PADDING, pady=(theme.PADDING, 2), sticky="we")
            inner_row += 1
        for field_name in field_names:
            inner_row = _render_field(group, inner_row, surface, field_name, specs)
        row += 1
    frame._field_specs = specs
    return frame


def read_value(widget) -> dict[str, object]:
    specs = getattr(widget, "_field_specs", None)
    if not isinstance(specs, dict):
        raise ValueError("Nested policy editor could not be read.")
    field_order = getattr(widget, "_field_order", None)
    names = field_order if isinstance(field_order, list) and field_order else list(specs)
    return {name: _read_field_value(name, specs[name]) for name in names if name in specs}


def grouped_fields(surface) -> list[tuple[str, list[str]]]:
    draft_fields = list(surface.draft)
    groups = surface.descriptor.get("field_groups", [])
    seen: set[str] = set()
    normalized = []
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            fields = [field for field in group.get("fields", []) if isinstance(field, str) and field in surface.draft and field not in seen]
            if not fields:
                continue
            seen.update(fields)
            normalized.append((str(group.get("label") or "").strip(), fields))
    remaining = [field for field in draft_fields if field not in seen]
    if remaining:
        normalized.append(("", remaining))
    return normalized or [("", draft_fields)]


def _render_field(parent, row: int, surface, field_name: str, specs: dict[str, dict]) -> int:
    labels = surface.descriptor.get("field_labels", {})
    hints = surface.descriptor.get("field_help", {})
    value = surface.draft.get(field_name)
    field = ctk.CTkFrame(parent, fg_color=parent.cget("fg_color"))
    field.grid(row=row, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
    field.grid_columnconfigure(0, weight=1)
    label = str(labels.get(field_name) or field_name)
    create_readonly_text(field, text=label, font=theme.font_normal(), min_lines=1, max_lines=2).grid(row=0, column=0, sticky="we")
    meta = field_name if label == field_name else f"{field_name}"
    if meta:
        create_readonly_text(field, text=meta, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=1).grid(
            row=1, column=0, pady=(2, 0), sticky="we"
        )
    hint = str(hints.get(field_name) or "").strip()
    widget_row = 2
    if hint:
        create_readonly_text(field, text=hint, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=3).grid(
            row=2, column=0, pady=(2, 0), sticky="we"
        )
        widget_row = 3
    kind = _field_kind(value)
    widget, spec = _field_widget(field, kind=kind, value=value)
    widget.grid(row=widget_row, column=0, pady=(theme.PADDING_SMALL, 0), sticky="we")
    specs[field_name] = {"kind": kind, "widget": widget, **spec}
    return row + 1


def _field_widget(parent, *, kind: str, value):
    if kind == "bool":
        variable = ctk.BooleanVar(value=bool(value))
        widget = ctk.CTkCheckBox(parent, text="Enabled", variable=variable, onvalue=True, offvalue=False)
        return widget, {"variable": variable}
    if kind == "string_list":
        widget = create_json_textbox(parent, height=_LIST_HEIGHT)
        widget.insert("1.0", "\n".join(value))
        return widget, {}
    if kind == "json_object":
        widget = create_json_textbox(parent, height=_JSON_HEIGHT)
        widget.insert("1.0", json.dumps(value, indent=2, ensure_ascii=False))
        return widget, {}
    widget = ctk.CTkEntry(parent, height=theme.INPUT_HEIGHT)
    widget.insert(0, "" if value is None else str(value))
    return widget, {}


def _read_field_value(field_name: str, spec: dict) -> object:
    kind = spec["kind"]
    widget = spec["widget"]
    if kind == "bool":
        return bool(spec["variable"].get())
    if kind == "int":
        raw = widget.get().strip()
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer.") from exc
    if kind == "float":
        raw = widget.get().strip()
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number.") from exc
    if kind == "string_list":
        return [line.strip() for line in widget.get("1.0", "end").splitlines() if line.strip()]
    if kind == "json_object":
        raw = widget.get("1.0", "end").strip() or "{}"
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"{field_name} must contain valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{field_name} must contain a JSON object.")
        return payload
    return widget.get().strip()


def _field_kind(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "string_list"
    if isinstance(value, dict):
        return "json_object"
    return "string"
