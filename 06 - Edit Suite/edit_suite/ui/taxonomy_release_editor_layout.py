"""Widget layout helpers for the Semantic Release editor."""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from . import theme
from .scoped_scroll import ScopedScrollableFrame
from .taxonomy_release_model import PROJECTION_LIST_FIELDS, TAXONOMY_SECTIONS
from .text_widgets import create_readonly_text


def render_source_controls(frame, actions: dict[str, Any]) -> None:
    controls = ctk.CTkFrame(frame)
    controls.grid(row=0, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    controls.grid_columnconfigure(1, weight=1)
    create_readonly_text(controls, text="Artifact Tree", font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=0, column=0, sticky="w")
    frame._artifact_root_entry = ctk.CTkEntry(controls, height=theme.INPUT_HEIGHT)
    frame._artifact_root_entry.insert(0, str(frame._draft.get("artifact_root") or ""))
    frame._artifact_root_entry.grid(row=0, column=1, padx=theme.PADDING_SMALL, sticky="we")
    ctk.CTkButton(controls, text="Browse", width=90, command=lambda target=frame: actions["browse_artifact_root"](target)).grid(row=0, column=2, sticky="e")
    ctk.CTkButton(controls, text="Scan", width=80, command=lambda target=frame: actions["scan_artifact_root"](target)).grid(row=0, column=3, padx=(theme.PADDING_SMALL, 0), sticky="e")

    create_readonly_text(controls, text="Semantic Release", font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=1, column=0, pady=(theme.PADDING_SMALL, 0), sticky="w")
    frame._candidate_var = ctk.StringVar(value="")
    frame._candidate_menu = ctk.CTkOptionMenu(controls, values=["No release loaded"], variable=frame._candidate_var)
    frame._candidate_menu.grid(row=1, column=1, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="we")
    ctk.CTkButton(controls, text="Load Copy", width=110, command=lambda target=frame: actions["load_selected_release"](target)).grid(row=1, column=2, columnspan=2, pady=(theme.PADDING_SMALL, 0), sticky="e")

    create_readonly_text(controls, text="Working Copy", font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=2, column=0, pady=(theme.PADDING_SMALL, 0), sticky="w")
    frame._working_release_entry = ctk.CTkEntry(controls, height=theme.INPUT_HEIGHT)
    frame._working_release_entry.insert(0, str(frame._draft.get("working_release_path") or ""))
    frame._working_release_entry.grid(row=2, column=1, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="we")

    create_readonly_text(controls, text="Current DB", font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=3, column=0, pady=(theme.PADDING_SMALL, 0), sticky="w")
    frame._corpus_db_entry = ctk.CTkEntry(controls, height=theme.INPUT_HEIGHT)
    frame._corpus_db_entry.insert(0, str(frame._draft.get("corpus_db_path") or ""))
    frame._corpus_db_entry.grid(row=3, column=1, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0), sticky="we")
    ctk.CTkButton(controls, text="Browse", width=90, command=lambda target=frame: actions["browse_corpus_db"](target)).grid(row=3, column=2, columnspan=2, pady=(theme.PADDING_SMALL, 0), sticky="e")


def render_release_summary(frame) -> None:
    frame._summary = create_readonly_text(frame, min_lines=3, max_lines=6, font=theme.font_small(), text_color=theme.COLOR_MUTED)
    frame._summary.grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="we")


def render_tabs(frame, actions: dict[str, Any]) -> None:
    frame._tabs = ctk.CTkTabview(frame)
    frame._tabs.grid(row=2, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="nsew")
    render_taxonomy_tab(frame, frame._tabs.add("Taxonomy"), actions)
    render_projection_tab(frame, frame._tabs.add("Projections"), actions)
    render_verify_tab(frame, frame._tabs.add("Verify"), actions)


def render_taxonomy_tab(frame, tab, actions: dict[str, Any]) -> None:
    tab.grid_columnconfigure(1, weight=1)
    header = ctk.CTkFrame(tab)
    header.grid(row=0, column=0, columnspan=2, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    frame._section_menu = ctk.CTkOptionMenu(header, values=list(TAXONOMY_SECTIONS), variable=frame._taxonomy_section, command=lambda _choice: actions["select_taxonomy_section"](frame))
    frame._section_menu.grid(row=0, column=0, sticky="w")
    for col, (label, command_key) in enumerate((("New", "new_taxonomy_item"), ("Duplicate", "duplicate_taxonomy_item"), ("Delete", "delete_taxonomy_item")), start=1):
        ctk.CTkButton(header, text=label, width=90, command=lambda key=command_key, target=frame: actions[key](target)).grid(row=0, column=col, padx=(theme.PADDING_SMALL, 0))
    frame._taxonomy_list = ScopedScrollableFrame(tab, width=280, height=330)
    frame._taxonomy_list.grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="nsw")
    detail = ctk.CTkFrame(tab)
    detail.grid(row=1, column=1, padx=(0, theme.PADDING_SMALL), pady=(0, theme.PADDING_SMALL), sticky="nsew")
    detail.grid_columnconfigure(1, weight=1)
    frame._taxonomy_widgets = {}
    row = 0
    for field_name in ("key", "label", "description", "aliases", "status", "parent_id"):
        create_readonly_text(detail, text=field_name, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=row, column=0, padx=(0, theme.PADDING_SMALL), pady=4, sticky="w")
        widget = ctk.CTkEntry(detail, height=theme.INPUT_HEIGHT)
        widget.grid(row=row, column=1, pady=4, sticky="we")
        frame._taxonomy_widgets[field_name] = widget
        row += 1


def render_projection_tab(frame, tab, actions: dict[str, Any]) -> None:
    tab.grid_columnconfigure(1, weight=1)
    header = ctk.CTkFrame(tab)
    header.grid(row=0, column=0, columnspan=2, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    for col, (label, command_key) in enumerate((("New", "new_projection"), ("Duplicate", "duplicate_projection"), ("Delete", "delete_projection"), ("Update Choices", "update_projection_choices"))):
        ctk.CTkButton(header, text=label, width=90, command=lambda key=command_key, target=frame: actions[key](target)).grid(row=0, column=col, padx=(0, theme.PADDING_SMALL))
    frame._projection_list = ScopedScrollableFrame(tab, width=280, height=420)
    frame._projection_list.grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="nsw")
    detail = ScopedScrollableFrame(tab, height=420)
    detail.grid(row=1, column=1, padx=(0, theme.PADDING_SMALL), pady=(0, theme.PADDING_SMALL), sticky="nsew")
    detail.grid_columnconfigure(1, weight=1)
    frame._projection_widgets = {}
    frame._projection_pickers = {}
    row = 0
    for field_name in ("projection_id", "label", "description"):
        row = entry_field(detail, frame._projection_widgets, field_name, row)
    for field_name in PROJECTION_LIST_FIELDS:
        row = picker_field(detail, frame, field_name, row)
    row = picker_field(detail, frame, "example_document_types", row)
    row = picker_field(detail, frame, "section_roles", row)
    row = picker_field(detail, frame, "party_roles", row)
    for field_name in ("when_to_use", "avoid_when", "text_markers"):
        row = text_field(detail, frame._projection_widgets, field_name, row)


def render_verify_tab(frame, tab, actions: dict[str, Any]) -> None:
    tab.grid_columnconfigure(0, weight=1)
    frame._verify_text = create_readonly_text(tab, min_lines=10, max_lines=18, font=theme.font_small(), text_color=theme.COLOR_MUTED)
    frame._verify_text.grid(row=0, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    ctk.CTkButton(tab, text="Verify", width=110, command=lambda target=frame: actions["trigger_verify"](target)).grid(row=1, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="w")


def entry_field(parent, widgets: dict, field_name: str, row: int) -> int:
    create_readonly_text(parent, text=field_name, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=row, column=0, padx=(0, theme.PADDING_SMALL), pady=4, sticky="w")
    widget = ctk.CTkEntry(parent, height=theme.INPUT_HEIGHT)
    widget.grid(row=row, column=1, pady=4, sticky="we")
    widgets[field_name] = widget
    return row + 1


def text_field(parent, widgets: dict, field_name: str, row: int) -> int:
    create_readonly_text(parent, text=field_name, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=row, column=0, padx=(0, theme.PADDING_SMALL), pady=4, sticky="nw")
    widget = ctk.CTkTextbox(parent, height=74, wrap="word", font=theme.font_normal())
    widget.grid(row=row, column=1, pady=4, sticky="we")
    widgets[field_name] = widget
    return row + 1


def picker_field(parent, frame, field_name: str, row: int) -> int:
    create_readonly_text(parent, text=field_name, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=row, column=0, padx=(0, theme.PADDING_SMALL), pady=4, sticky="nw")
    picker = ScopedScrollableFrame(parent, height=118)
    picker.grid(row=row, column=1, pady=4, sticky="we")
    picker.grid_columnconfigure(0, weight=1)
    frame._projection_pickers[field_name] = {"container": picker, "vars": {}, "options": []}
    return row + 1
