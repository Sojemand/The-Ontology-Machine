"""Section-intro cards for the Edit Suite detail view."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .text_widgets import create_readonly_text


def render_section_intro(container, section_name: str, headline: str, body: str, *, row: int) -> int:
    card = ctk.CTkFrame(container)
    card.grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    card.grid_columnconfigure(0, weight=1)
    min_lines, max_lines = section_body_limits(section_name, body)
    create_readonly_text(
        card,
        text=headline,
        font=theme.font_header(),
        min_lines=1,
        max_lines=2,
        height=theme.INPUT_HEIGHT,
    ).grid(row=0, column=0, padx=theme.PADDING, pady=(theme.PADDING, 2), sticky="we")
    create_readonly_text(
        card,
        text=body,
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        min_lines=min_lines,
        max_lines=max_lines,
    ).grid(row=1, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="we")
    return row + 1


def section_body_limits(section_name: str, body: str) -> tuple[int, int]:
    line_count = max(1, body.count("\n") + 1)
    if section_name == "Summary":
        min_lines = max(2, min(8, line_count))
        return min_lines, max(min_lines, line_count)
    return 2, 6
