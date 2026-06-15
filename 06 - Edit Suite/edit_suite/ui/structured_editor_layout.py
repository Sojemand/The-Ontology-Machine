"""Shared layout fragments for structured source-package editors."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .scoped_scroll import ScopedScrollableFrame
from .text_widgets import create_json_textbox


def render_action_bar(parent, *, row: int, columnspan: int, actions: tuple[tuple[str, object], ...], target) -> None:
    frame = ctk.CTkFrame(parent)
    frame.grid(row=row, column=0, columnspan=columnspan, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    for column, (label, command) in enumerate(actions):
        ctk.CTkButton(frame, text=label, width=90, command=lambda fn=command: fn(target)).grid(row=0, column=column, padx=(0, 6))


def render_split_editor(parent, *, row: int, list_width: int, tab_width: int | None = None):
    listing = ScopedScrollableFrame(parent, width=list_width)
    listing.grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=(0, theme.PADDING_SMALL), sticky="nsw")
    tabs = ctk.CTkTabview(parent, width=tab_width) if tab_width is not None else ctk.CTkTabview(parent)
    tabs.grid(row=row, column=1, padx=(0, theme.PADDING_SMALL), pady=(0, theme.PADDING_SMALL), sticky="nsew")
    structured = tabs.add("Structured")
    structured.grid_columnconfigure(0, weight=1)
    debug = tabs.add("Debug JSON")
    debug.grid_columnconfigure(0, weight=1)
    raw = create_json_textbox(debug, height=360)
    raw.grid(row=0, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="nsew")
    raw.configure(state="disabled")
    return listing, structured, tabs, raw
