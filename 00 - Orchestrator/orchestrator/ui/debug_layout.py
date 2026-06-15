"""Surface stage for the orchestrator debug-host tab layout."""

from __future__ import annotations

import customtkinter as ctk

from . import responsive, theme
from .debug_controls_layout import build_debug_console
from .debug_monitor_layout import build_debug_monitor
from .debug_results_layout import build_debug_results


def build_debug_tab(app, parent) -> None:
    app._debug_scroll_body = responsive.make_scroll_body(parent)
    body = app._debug_scroll_body
    header = ctk.CTkFrame(body, fg_color="transparent")
    header.pack(fill="x", pady=(0, 0))
    ctk.CTkLabel(header, text="Debug Host", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(side="left")
    app._debug_reset_output_btn = ctk.CTkButton(
        header,
        text="Reset Debug Output",
        height=theme.BUTTON_HEIGHT,
        fg_color=theme.COLOR_ERROR,
        hover_color=theme.COLOR_ERROR,
        command=app._reset_debug_output,
    )
    app._debug_reset_output_btn.pack(side="right")
    ctk.CTkLabel(
        body,
        text="Descriptor-driven sibling-module launches, live status, and artifact inspection for power users.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        justify="left",
    ).pack(fill="x", pady=(2, theme.PADDING_SMALL))
    build_debug_console(app, body)
    build_debug_monitor(app, body)
    build_debug_results(app, body)
