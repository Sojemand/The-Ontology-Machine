"""Generic typed form widgets for owner-provided leaf-map surfaces."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .text_widgets import create_json_textbox, create_readonly_text

COMPACT_EDITOR_WIDTH = 1180
LIST_EDITOR_HEIGHT = 112


def render_form_editor(parent, surface, *, width: int):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1 if uses_compact_form_layout(width) else 0)
    frame.grid_columnconfigure(1, weight=0 if uses_compact_form_layout(width) else 1)
    row = 0
    fields: dict[str, dict] = {}
    for label, field_names in grouped_fields(surface):
        if label:
            create_readonly_text(
                frame,
                text=label,
                font=theme.font_small(),
                text_color=theme.COLOR_MUTED,
                min_lines=1,
                max_lines=1,
                height=theme.INPUT_HEIGHT,
            ).grid(row=row, column=0, columnspan=2, pady=(theme.PADDING_SMALL, 0), sticky="w")
            row += 1
        for field_name in field_names:
            row = _render_field(frame, row, field_name, surface.draft.get(field_name), fields, compact=uses_compact_form_layout(width))
    frame._form_fields = fields
    frame._entries = {name: spec["widget"] for name, spec in fields.items() if spec["kind"] in {"string", "int", "float"}}
    return frame


def read_form_value(widget) -> dict[str, object]:
    fields = getattr(widget, "_form_fields", None)
    if isinstance(fields, dict):
        return {name: _read_field_value(name, spec) for name, spec in fields.items()}
    entries = getattr(widget, "_entries", None)
    if isinstance(entries, dict):
        return {name: entry.get() for name, entry in entries.items()}
    raise ValueError("Form could not be read.")


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


def uses_compact_form_layout(width: int) -> bool:
    return width < COMPACT_EDITOR_WIDTH


def _render_field(parent, row: int, field_name: str, value, fields: dict[str, dict], *, compact: bool) -> int:
    label = create_readonly_text(
        parent,
        text=field_name,
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        min_lines=1,
        max_lines=2,
        height=theme.INPUT_HEIGHT,
    )
    kind = _field_kind(value)
    if kind == "bool":
        variable = ctk.BooleanVar(value=bool(value))
        widget = ctk.CTkCheckBox(parent, text="Enabled", variable=variable, onvalue=True, offvalue=False)
        fields[field_name] = {"kind": kind, "widget": widget, "variable": variable}
        return _place_single_line_field(label, widget, row=row, compact=compact)
    if kind == "list":
        widget = create_json_textbox(parent, height=LIST_EDITOR_HEIGHT)
        widget.insert("1.0", "\n".join(value))
        fields[field_name] = {"kind": kind, "widget": widget}
        return _place_multiline_field(label, widget, row=row)
    widget = ctk.CTkEntry(parent, height=theme.INPUT_HEIGHT)
    widget.insert(0, "" if value is None else str(value))
    fields[field_name] = {"kind": kind, "widget": widget}
    return _place_single_line_field(label, widget, row=row, compact=compact)


def _place_single_line_field(label, widget, *, row: int, compact: bool) -> int:
    label.grid(row=row, column=0, padx=(0, theme.PADDING_SMALL), pady=theme.PADDING_SMALL, sticky="w")
    if compact:
        widget.grid(row=row + 1, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
        return row + 2
    widget.grid(row=row, column=1, pady=theme.PADDING_SMALL, sticky="we")
    return row + 1


def _place_multiline_field(label, widget, *, row: int) -> int:
    label.grid(row=row, column=0, columnspan=2, padx=(0, theme.PADDING_SMALL), pady=theme.PADDING_SMALL, sticky="w")
    widget.grid(row=row + 1, column=0, columnspan=2, pady=(0, theme.PADDING_SMALL), sticky="we")
    return row + 2


def _read_field_value(field_name: str, spec: dict) -> object:
    kind = spec["kind"]
    widget = spec["widget"]
    if kind == "bool":
        return _coerce_bool(spec.get("variable").get(), field_name=field_name)
    if kind == "list":
        return [line.strip() for line in widget.get("1.0", "end").splitlines() if line.strip()]
    raw = widget.get().strip()
    if kind == "int":
        return _parse_int(raw, field_name=field_name)
    if kind == "float":
        return _parse_float(raw, field_name=field_name)
    return raw


def _field_kind(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "list"
    return "string"


def _coerce_bool(value, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field_name} must be true or false")


def _parse_int(value: str, *, field_name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _parse_float(value: str, *, field_name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number") from exc
