"""Readonly summary-card rendering for the Edit Suite."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .text_widgets import create_readonly_text


def render_summary_card(container, card, *, row: int) -> int:
    frame = ctk.CTkFrame(container)
    frame.grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    frame.grid_columnconfigure(0, weight=1)
    create_readonly_text(
        frame,
        text=card.label,
        font=theme.font_header(),
        min_lines=1,
        max_lines=2,
        height=theme.INPUT_HEIGHT,
    ).grid(row=0, column=0, padx=theme.PADDING, pady=(theme.PADDING, 2), sticky="we")
    if card.body:
        create_readonly_text(
            frame,
            text=card.body,
            font=theme.font_small(),
            text_color=theme.COLOR_MUTED,
            min_lines=1,
            max_lines=4,
        ).grid(row=1, column=0, padx=theme.PADDING, pady=(0, 2), sticky="we")
    if card.lines:
        create_readonly_text(
            frame,
            text="\n".join(card.lines),
            font=theme.font_small(),
            min_lines=min(2, len(card.lines)),
            max_lines=max(2, min(10, len(card.lines))),
        ).grid(row=2, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="we")
    return row + 1
