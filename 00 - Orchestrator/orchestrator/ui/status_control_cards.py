from __future__ import annotations

import customtkinter as ctk

from . import theme


def build_release_mode_card(app, parent) -> object:
    card = ctk.CTkFrame(parent)
    ctk.CTkLabel(card, text="Semantic Release Mode", font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    ctk.CTkLabel(
        card,
        text="Choose whether the run uses the database's active release or deliberately overrides it with a selected release.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        justify="left",
        wraplength=320,
    ).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(4, 0))
    app._semantic_release_mode_var = ctk.StringVar(value="DB Release")
    app._semantic_release_mode_selector = ctk.CTkSegmentedButton(
        card,
        values=["DB Release", "Override Release"],
        variable=app._semantic_release_mode_var,
        command=lambda _value: app._on_semantic_release_mode_change(),
    )
    app._semantic_release_mode_selector.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    return card


def build_control_card(app, parent) -> object:
    card = ctk.CTkFrame(parent)
    ctk.CTkLabel(card, text="Run Control", font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    options = ctk.CTkFrame(card, fg_color="transparent")
    options.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(options, text="Mode:", font=theme.font_normal()).pack(side="left")
    app._mode_var = ctk.StringVar(value="batch")
    app._mode_selector = ctk.CTkSegmentedButton(options, values=["batch", "single"], variable=app._mode_var, command=lambda _value: app._on_mode_change())
    app._mode_selector.pack(side="left", padx=(8, 0), fill="x", expand=True)
    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    app._create_artifact_tree_btn = ctk.CTkButton(actions, text="Create Artifact Tree", height=theme.ACTION_BUTTON_HEIGHT, font=theme.font_header(), command=app._create_artifact_tree)
    app._start_btn = ctk.CTkButton(actions, text="Process", height=theme.ACTION_BUTTON_HEIGHT, font=theme.font_header(), command=app._start_processing)
    app._reset_btn = ctk.CTkButton(actions, text="Reset Error Bundle", height=theme.ACTION_BUTTON_HEIGHT, font=theme.font_header(), fg_color=theme.COLOR_ERROR, hover_color=theme.COLOR_ERROR, command=app._reset_run_history)
    reset_logs_command = getattr(app, "_reset_pipeline_logs", app._reset_run_history)
    app._reset_pipeline_logs_btn = ctk.CTkButton(actions, text="Reset Pipeline Logs", height=theme.ACTION_BUTTON_HEIGHT, font=theme.font_header(), fg_color=theme.COLOR_ERROR, hover_color=theme.COLOR_ERROR, command=reset_logs_command)
    app._abort_btn = ctk.CTkButton(actions, text="Abort", height=theme.ACTION_BUTTON_HEIGHT, font=theme.font_header(), fg_color=theme.COLOR_WARNING, hover_color=theme.COLOR_WARNING, command=app._abort_processing)
    app._open_edit_suite_btn = ctk.CTkButton(actions, text="Open Edit Suite", height=theme.BUTTON_HEIGHT, command=app._open_edit_suite)
    app._status_help_btn = ctk.CTkButton(actions, text="Help", height=theme.BUTTON_HEIGHT, command=app._show_status_help)
    for widget in (app._create_artifact_tree_btn, app._start_btn, app._reset_btn, app._reset_pipeline_logs_btn, app._abort_btn, app._open_edit_suite_btn, app._status_help_btn):
        widget.pack(fill="x", pady=(0, 6))
    return card
