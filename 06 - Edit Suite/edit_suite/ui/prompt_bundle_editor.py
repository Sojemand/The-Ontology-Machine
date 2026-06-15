"""Prompt-bundle editor widgets for the Edit Suite."""
from __future__ import annotations

import re

import customtkinter as ctk

from . import theme
from .text_widgets import create_json_textbox, create_readonly_text

PROMPT_BUNDLE_EDITOR_HEIGHT = 340
_ORDER = ("system_prompt_md", "user_prompt_rules_md", "output_schema_json", "projection_hint_policy_md")
_LABELS = {
    "ocr_prompt_md": "OCR Prompt",
    "system_prompt_md": "System Prompt",
    "user_prompt_rules_md": "User Prompt",
    "output_schema_json": "Output Schema",
    "projection_hint_policy_md": "Projection Hint",
}
_SOURCES = {
    "ocr_prompt_md": "config/optimizer_ocr_prompt.md",
    "system_prompt_md": "config/prompt_bundle/system_prompt.md",
    "user_prompt_rules_md": "config/prompt_bundle/user_prompt_rules.md",
    "output_schema_json": "config/prompt_bundle/output_schema.json",
    "projection_hint_policy_md": "config/prompt_bundle/projection_hint_policy.md",
}


def render(parent, surface):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    tabs = ctk.CTkTabview(frame)
    tabs.grid(row=0, column=0, sticky="nsew")
    data = values(surface.draft)
    editors = {}
    actual = tabs.add("Actual")
    actual.grid_columnconfigure(0, weight=1)
    create_readonly_text(actual, text="Lesbare Gesamtansicht des Prompt Bundles.", font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(
        row=0, column=0, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="we"
    )
    actual_preview = create_json_textbox(actual, height=PROMPT_BUNDLE_EDITOR_HEIGHT)
    actual_preview.configure(font=theme.font_normal())
    actual_preview.grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="nsew")
    for label, field_name in fields(surface.draft):
        tab = tabs.add(label)
        tab.grid_columnconfigure(0, weight=1)
        create_readonly_text(tab, text=_SOURCES.get(field_name, field_name), font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(
            row=0, column=0, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="we"
        )
        textbox = create_json_textbox(tab, height=PROMPT_BUNDLE_EDITOR_HEIGHT)
        if field_name != "output_schema_json":
            textbox.configure(font=theme.font_normal())
        textbox.grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="nsew")
        _set_textbox_text(textbox, data.get(field_name, ""))
        _bind_preview_refresh(textbox, lambda _event=None, target=frame: refresh_actual(target))
        editors[field_name] = textbox
    frame._bundle_inputs = editors
    frame._actual_preview = actual_preview
    frame._bundle_field_order = tuple(field_name for _label, field_name in fields(surface.draft))
    refresh_actual(frame)
    return frame


def read_value(widget) -> dict[str, str]:
    return {name: entry.get("1.0", "end").strip() for name, entry in widget._bundle_inputs.items()}


def fields(payload: dict) -> list[tuple[str, str]]:
    if not isinstance(payload, dict):
        return []
    ordered = [field_name for field_name in _ORDER if field_name in payload]
    ordered.extend(field_name for field_name in payload if field_name not in ordered)
    return [(label(field_name), field_name) for field_name in ordered]


def values(payload: dict) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    return {field_name: string_value(payload.get(field_name)) for _label, field_name in fields(payload)}


def refresh_actual(widget) -> None:
    data = {name: editor.get("1.0", "end").strip() for name, editor in widget._bundle_inputs.items()}
    _set_textbox_text(widget._actual_preview, actual_text(data), readonly=True)


def actual_text(values_map: dict[str, str]) -> str:
    blocks = []
    for heading, field_name in fields(values_map):
        body = values_map.get(field_name, "").strip() or "(leer)"
        blocks.append(f"{heading}\n{'=' * len(heading)}\n{body}")
    return "\n\n".join(blocks) if blocks else "No prompt bundle content loaded."


def label(field_name: str) -> str:
    if field_name in _LABELS:
        return _LABELS[field_name]
    return re.sub(r"\s+", " ", field_name.replace("_", " ")).strip().title()


def string_value(value) -> str:
    if isinstance(value, str):
        return value
    return "" if value is None else str(value)


def _bind_preview_refresh(textbox, callback) -> None:
    inner = getattr(textbox, "_textbox", textbox)
    for sequence in ("<KeyRelease>", "<FocusOut>", "<<Paste>>", "<<Cut>>"):
        inner.bind(sequence, callback, add="+")


def _set_textbox_text(textbox, text: str, *, readonly: bool = False) -> None:
    textbox.configure(state="normal")
    textbox.delete("1.0", "end")
    textbox.insert("1.0", text)
    if readonly:
        textbox.configure(state="disabled")
