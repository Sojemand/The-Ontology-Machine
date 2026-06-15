"""Reusable field rendering for structured source-package editors."""
from __future__ import annotations

import json

import customtkinter as ctk

from . import theme
from .payload_paths import get_nested
from .slot_hints import render_slot_hint, resolve_descriptor
from .text_widgets import create_json_textbox, create_readonly_text


def render_field(widget, payload: dict, field_path: str, row: int, *, prefix: str = "", list_only: bool = False, pady=(2, None)) -> int:
    create_readonly_text(
        widget._detail_frame,
        text=field_path,
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
    ).grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="w")
    row = render_slot_hint(
        widget._detail_frame,
        resolve_descriptor(widget._slot_descriptors, field_path, prefix=prefix),
        row=row + 1,
    )
    value = get_nested(payload, field_path)
    if isinstance(value, list) or (isinstance(value, dict) and not list_only):
        editor = create_json_textbox(widget._detail_frame, height=96)
        editor.insert("1.0", json.dumps(value, indent=2, ensure_ascii=False))
        default = "[]" if isinstance(value, list) else "{}"
        widget._detail_widgets[field_path] = lambda source=editor, fallback=default: json.loads(source.get("1.0", "end").strip() or fallback)
    else:
        editor = ctk.CTkEntry(widget._detail_frame, height=theme.INPUT_HEIGHT)
        editor.insert(0, "" if value is None else str(value))
        widget._detail_widgets[field_path] = editor.get
    bottom = theme.PADDING_SMALL if pady[1] is None else pady[1]
    editor.grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=(pady[0], bottom), sticky="we")
    return row + 1
