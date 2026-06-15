"""UI surface layout construction for the Orchestrator desktop app."""

from __future__ import annotations

import customtkinter as ctk

from .credentials_layout import build_credentials_tab
from .debug_layout import build_debug_tab
from . import lazy_tabs, rendering
from .model_settings_layout import build_model_settings_tab
from .status_layout import build_status_tab
from . import responsive, theme


def build_ui(app) -> None:
    responsive.activate_resize(app)
    main = ctk.CTkFrame(app)
    main.pack(fill="both", expand=True, padx=theme.PADDING, pady=theme.PADDING)
    _build_header(main)
    app._tabs = ctk.CTkTabview(main, command=lambda: lazy_tabs.on_tab_selected(app))
    app._tabs.pack(fill="both", expand=True, pady=(theme.PADDING_SMALL, 0))
    lazy_tabs.configure(app)
    lazy_tabs.register_tab(app, lazy_tabs.STATUS_TAB, _build_status_surface)
    lazy_tabs.register_tab(app, lazy_tabs.DEBUG_TAB, _build_debug_surface)
    lazy_tabs.register_tab(app, lazy_tabs.CREDENTIALS_TAB, _build_credentials_surface)
    lazy_tabs.register_tab(app, lazy_tabs.MODELS_TAB, _build_model_surface)
    lazy_tabs.register_tab(app, lazy_tabs.LOG_TAB, _build_log_surface)
    lazy_tabs.activate_initial_tab(app, lazy_tabs.STATUS_TAB)


def _build_header(parent) -> None:
    ctk.CTkLabel(parent, text="Orchestrator", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(anchor="w")
    ctk.CTkLabel(
        parent,
        text="Central operator client for routing, pipeline control, and sibling-module debugging.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
    ).pack(anchor="w", pady=(2, 0))


def _build_log_tab(app, parent) -> None:
    app._log_scroll_body = responsive.make_scroll_body(parent)
    body = app._log_scroll_body
    ctk.CTkLabel(body, text="Run Log", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(
        anchor="w",
        pady=(0, 0),
    )
    app._log_box = ctk.CTkTextbox(body, font=theme.font_mono(), height=560)
    app._log_box.pack(fill="both", expand=True, pady=(theme.PADDING_SMALL, 0))
    app._log_box.configure(state="disabled")


def _build_status_surface(app, parent) -> None:
    build_status_tab(app, parent)


def _build_debug_surface(app, parent) -> None:
    build_debug_tab(app, parent)
    if hasattr(app, "_initialize_debug_tab"):
        app._initialize_debug_tab()


def _build_credentials_surface(app, parent) -> None:
    build_credentials_tab(app, parent)
    if hasattr(app, "_initialize_credentials_tab"):
        app._initialize_credentials_tab()


def _build_model_surface(app, parent) -> None:
    build_model_settings_tab(app, parent)
    if hasattr(app, "_initialize_model_settings_tab"):
        app._initialize_model_settings_tab()


def _build_log_surface(app, parent) -> None:
    _build_log_tab(app, parent)
    rendering.sync_log_box(app)
