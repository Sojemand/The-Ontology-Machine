"""Inspection pane layout for the orchestrator debug-host tab."""

from __future__ import annotations

import customtkinter as ctk

from . import responsive, theme

_ARTIFACT_LIST_HEIGHT = 220
_INSPECTOR_HEIGHT = 320
_TEXTBOX_HEIGHT = 220


def build_debug_results(app, parent) -> None:
    app._debug_results_frame = ctk.CTkFrame(parent, fg_color="transparent")
    app._debug_results_frame.pack(fill="x", padx=theme.PADDING, pady=(0, theme.PADDING))
    app._debug_artifact_panel = ctk.CTkFrame(app._debug_results_frame)
    app._debug_inspector_panel = ctk.CTkFrame(app._debug_results_frame)
    _build_artifact_panel(app)
    _build_inspector_panel(app)
    responsive.register_resize_callback(app, "debug_results", lambda width: _apply_layout(app, width))


def _build_artifact_panel(app) -> None:
    ctk.CTkLabel(app._debug_artifact_panel, text="Artifacts", font=theme.font_normal(), text_color=theme.COLOR_TEXT).pack(anchor="w", padx=10, pady=(10, 0))
    app._debug_artifact_summary_label = ctk.CTkLabel(app._debug_artifact_panel, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left")
    app._debug_artifact_summary_label.pack(fill="x", padx=10, pady=(theme.PADDING_SMALL, 6))
    app._debug_artifact_buttons_frame = ctk.CTkScrollableFrame(app._debug_artifact_panel, height=_ARTIFACT_LIST_HEIGHT)
    app._debug_artifact_buttons_frame.pack(fill="x", expand=True, padx=10, pady=(0, 10))


def _build_inspector_panel(app) -> None:
    app._debug_results_tabs = ctk.CTkTabview(app._debug_inspector_panel, height=_INSPECTOR_HEIGHT)
    app._debug_results_tabs.pack(fill="x", expand=True, padx=10, pady=10)
    preview_tab = app._debug_results_tabs.add("Preview")
    log_tab = app._debug_results_tabs.add("run.log")
    replay_tab = app._debug_results_tabs.add("Replay")
    app._debug_results_tabs.set("Preview")
    app._debug_preview_box = _text_box(preview_tab)
    app._debug_log_box = _text_box(log_tab)
    ctk.CTkLabel(replay_tab, text="Replay / Import", font=theme.font_normal(), text_color=theme.COLOR_TEXT).pack(anchor="w", padx=10, pady=(10, 0))
    row = ctk.CTkFrame(replay_tab, fg_color="transparent")
    row.pack(fill="x", padx=10, pady=(theme.PADDING_SMALL, 0))
    app._debug_artifact_import_entry = ctk.CTkEntry(row, height=theme.INPUT_HEIGHT)
    app._debug_artifact_import_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    app._debug_artifact_import_entry.bind("<KeyRelease>", lambda _event: app._on_debug_change())
    app._debug_artifact_import_entry.bind("<FocusOut>", lambda _event: app._flush_pending_save("debug_state"))
    app._debug_replay_load_file_btn = ctk.CTkButton(row, text="Load file", width=96, command=app._load_debug_artifact_file)
    app._debug_replay_load_file_btn.pack(side="left", padx=(0, 6))
    app._debug_replay_load_dir_btn = ctk.CTkButton(row, text="Load dir", width=92, command=app._load_debug_artifact_dir)
    app._debug_replay_load_dir_btn.pack(side="left", padx=(0, 6))
    app._debug_replay_clear_btn = ctk.CTkButton(row, text="Clear", width=76, command=app._clear_debug_artifact_import)
    app._debug_replay_clear_btn.pack(side="left")
    app._debug_replay_status_label = ctk.CTkLabel(replay_tab, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left")
    app._debug_replay_status_label.pack(fill="x", padx=10, pady=(theme.PADDING_SMALL, 0))
    app._debug_replay_box = _text_box(replay_tab)


def _text_box(parent):
    box = ctk.CTkTextbox(parent, height=_TEXTBOX_HEIGHT, font=theme.font_mono())
    box.pack(fill="x", expand=True, padx=10, pady=10)
    box.configure(state="disabled")
    return box


def _apply_layout(app, width: int) -> None:
    two_columns = width >= 1120
    if not responsive.remember_layout_key(app, "debug_results", two_columns):
        return
    for panel in (app._debug_artifact_panel, app._debug_inspector_panel):
        if hasattr(panel, "grid_forget"):
            panel.grid_forget()
    if hasattr(app._debug_results_frame, "grid_columnconfigure"):
        app._debug_results_frame.grid_columnconfigure(0, weight=1)
        app._debug_results_frame.grid_columnconfigure(1, weight=2 if two_columns else 1)
    if two_columns:
        app._debug_artifact_panel.grid(row=0, column=0, sticky="new", padx=(0, 6))
        app._debug_inspector_panel.grid(row=0, column=1, sticky="new", padx=(6, 0))
        return
    app._debug_artifact_panel.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    app._debug_inspector_panel.grid(row=1, column=0, sticky="ew", pady=(6, 0))
