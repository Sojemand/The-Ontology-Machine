"""Session monitor layout for the orchestrator debug-host tab."""

from __future__ import annotations

import customtkinter as ctk

from . import responsive, theme


def build_debug_monitor(app, parent) -> None:
    app._debug_monitor_frame = ctk.CTkFrame(parent)
    app._debug_monitor_frame.pack(fill="x", padx=theme.PADDING, pady=(0, theme.PADDING_SMALL))
    ctk.CTkLabel(
        app._debug_monitor_frame,
        text="Session Monitor",
        font=theme.font_normal(),
        text_color=theme.COLOR_TEXT,
    ).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    app._debug_monitor_wrap_labels = []
    app._debug_plan_label = _value_label(app, "Plan: derived from module and mode.")
    app._debug_status_label = ctk.CTkLabel(
        app._debug_monitor_frame,
        text="Ready",
        font=theme.font_normal(),
        text_color=theme.COLOR_TEXT,
        justify="left",
    )
    app._debug_status_label.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._debug_detail_label = _value_label(app, "No session started yet.")
    app._debug_metrics_label = _value_label(app, "")
    responsive.register_resize_callback(app, "debug_monitor", lambda width: _apply_layout(app, width))


def _value_label(app, text: str):
    label = ctk.CTkLabel(
        app._debug_monitor_frame,
        text=text,
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        justify="left",
    )
    label.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._debug_monitor_wrap_labels.append(label)
    return label


def _apply_layout(app, width: int) -> None:
    wrap = responsive.wrap_for_columns(width, 1, minimum=320, maximum=900, padding=220)
    if not responsive.remember_layout_key(app, "debug_monitor", wrap):
        return
    for label in getattr(app, "_debug_monitor_wrap_labels", []):
        responsive.set_wrap(label, wrap)
    responsive.set_wrap(getattr(app, "_debug_status_label", None), wrap)
