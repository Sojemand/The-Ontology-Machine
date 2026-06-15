"""Responsive status tab layout for the Orchestrator UI."""

from __future__ import annotations

import customtkinter as ctk

from ..models import STAGE_NAMES
from . import responsive, theme, view_model
from .status_control_cards import build_control_card, build_release_mode_card

_COUNTER_NAMES = ("Pending", "Success", "Errors", "Needs Review", "Retries")
_PATH_ROWS = (
    ("_input_entry", "Input Folder", "_browse_input_folder"),
    ("_artifact_entry", "Artifact Folder", "_browse_artifact_folder"),
    ("_corpus_entry", "Database Storage Folder", "_browse_corpus_folder", "Create Database", "_create_database"),
    ("_selected_db_entry", "Selected Database", "_browse_database_file"),
    ("_release_entry", "Semantic Release", "_browse_release_file", "Activate", "_activate_selected_release"),
)
_ROUTE_FIELDS = ("Route Family", "Optimizer", "Interpreter", "Intake Reason")
_DATABASE_FIELDS = ("Selected Database", "DB State", "Active DB Release", "Run Release")


def build_status_tab(app, parent) -> None:
    app._status_scroll_body = responsive.make_scroll_body(parent)
    body = app._status_scroll_body
    _build_header(app, body)
    _build_setup_cards(app, body)
    _build_progress_card(app, body)
    _build_summary_cards(app, body)
    _build_stage_cards(app, body)
    responsive.register_resize_callback(app, "status_tab", lambda width: _apply_responsive_layout(app, width))


def _build_header(app, parent) -> None:
    ctk.CTkLabel(parent, text="Status", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(anchor="w")
    ctk.CTkLabel(
        parent,
        text="Central operator surface for intake, pipeline runs, and artifact status.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
    ).pack(anchor="w", pady=(2, theme.PADDING_SMALL))


def _build_setup_cards(app, parent) -> None:
    app._setup_card_grid = ctk.CTkFrame(parent, fg_color="transparent")
    app._setup_card_grid.pack(fill="x", pady=(0, theme.PADDING_SMALL))
    app._setup_cards = [
        _build_path_card(
            app,
            app._setup_card_grid,
            label,
            getattr(app, browse_name),
            secondary_text=secondary_text if len(row) > 3 else "",
            secondary_command=getattr(app, secondary_name, None) if len(row) > 4 else None,
        )
        for row in _PATH_ROWS
        for _, label, browse_name, *rest in [row]
        for secondary_text, secondary_name in [((rest[0], rest[1]) if len(rest) == 2 else ("", ""))]
    ]
    app._setup_cards.append(build_release_mode_card(app, app._setup_card_grid))
    app._setup_cards.append(build_control_card(app, app._setup_card_grid))


def _build_progress_card(app, parent) -> None:
    card = ctk.CTkFrame(parent)
    card.pack(fill="x", pady=(0, theme.PADDING_SMALL))
    ctk.CTkLabel(card, text="Run Status", font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    app._progress = ctk.CTkProgressBar(card, progress_color=theme.COLOR_ACCENT)
    app._progress.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._progress.set(0.0)
    app._status_label = ctk.CTkLabel(card, text="", font=theme.font_normal(), text_color=theme.COLOR_TEXT, justify="left")
    app._status_label.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))


def _build_summary_cards(app, parent) -> None:
    app._counter_card_grid = ctk.CTkFrame(parent, fg_color="transparent")
    app._counter_card_grid.pack(fill="x", pady=(0, theme.PADDING_SMALL))
    app._counter_labels = {}
    app._counter_cards = [_build_value_card(app._counter_card_grid, name, app._counter_labels, font=theme.font_header()) for name in _COUNTER_NAMES]
    app._database_card_grid = ctk.CTkFrame(parent, fg_color="transparent")
    app._database_card_grid.pack(fill="x", pady=(0, theme.PADDING_SMALL))
    app._database_labels = {}
    app._database_cards = [_build_value_card(app._database_card_grid, name, app._database_labels, font=theme.font_normal(), justify="left") for name in _DATABASE_FIELDS]
    app._route_card_grid = ctk.CTkFrame(parent, fg_color="transparent")
    app._route_card_grid.pack(fill="x", pady=(0, theme.PADDING_SMALL))
    app._route_labels = {}
    app._route_cards = [_build_value_card(app._route_card_grid, name, app._route_labels, font=theme.font_normal(), justify="left") for name in _ROUTE_FIELDS]


def _build_stage_cards(app, parent) -> None:
    ctk.CTkLabel(parent, text="Pipeline Status", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(anchor="w", pady=(4, 4))
    app._stage_card_grid = ctk.CTkFrame(parent, fg_color="transparent")
    app._stage_card_grid.pack(fill="both", expand=True)
    app._stage_labels = {}
    app._stage_detail_labels = []
    app._stage_cards = []
    for name in STAGE_NAMES:
        card = ctk.CTkFrame(app._stage_card_grid)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)
        card.grid_columnconfigure(2, weight=0)
        ctk.CTkLabel(card, text=name, font=theme.font_normal()).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 2))
        progress = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED)
        progress.grid(row=0, column=1, sticky="e", padx=(6, 6), pady=(10, 2))
        status = ctk.CTkLabel(card, text=theme.STATUS_READY, font=theme.font_small(), text_color=view_model.stage_text_color(theme.STATUS_READY))
        status.grid(row=0, column=2, sticky="e", padx=(6, 10), pady=(10, 2))
        detail = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left")
        detail.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        app._stage_labels[name] = (status, detail, progress)
        app._stage_detail_labels.append(detail)
        app._stage_cards.append(card)


def _build_path_card(app, parent, label: str, command, *, secondary_text: str = "", secondary_command=None) -> object:
    card = ctk.CTkFrame(parent)
    ctk.CTkLabel(card, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    row = ctk.CTkFrame(card, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    entry = ctk.CTkEntry(row, height=theme.INPUT_HEIGHT)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    entry.bind("<KeyRelease>", lambda _event: app._on_ui_change())
    entry.bind("<FocusOut>", lambda _event: app._flush_pending_save("ui_state"))
    browse_button = ctk.CTkButton(row, text="Select", width=90, height=theme.BUTTON_HEIGHT, command=command)
    browse_button.pack(side="left", padx=(0, 6 if secondary_command else 0))
    if secondary_command is not None:
        action_button = ctk.CTkButton(row, text=secondary_text or "Action", width=90, height=theme.BUTTON_HEIGHT, command=secondary_command)
        action_button.pack(side="left")
        if label == "Semantic Release":
            app._activate_release_btn = action_button
        if label == "Database Storage Folder":
            app._create_database_btn = action_button
    if label == "Semantic Release":
        app._release_browse_btn = browse_button
    setattr(app, _attribute_name(label), entry)
    return card


def _build_value_card(parent, name: str, labels: dict[str, object], *, font, justify: str = "center") -> object:
    card = ctk.CTkFrame(parent)
    ctk.CTkLabel(card, text=name, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=10, pady=(8, 0))
    value = ctk.CTkLabel(card, text="0" if justify == "center" else "-", font=font, justify=justify)
    value.pack(anchor="w", padx=10, pady=(0, 8))
    labels[name] = value
    return card


def _apply_responsive_layout(app, width: int) -> None:
    stage_columns = responsive.columns_for(width, compact=860, wide=1220, maximum=3)
    layout_key = (
        responsive.columns_for(width, compact=900, wide=1180, maximum=2),
        responsive.columns_for(width, compact=780, wide=1160, maximum=5),
        responsive.columns_for(width, compact=860, wide=1180, maximum=2),
        responsive.columns_for(width, compact=860, wide=1180, maximum=2),
        stage_columns,
        responsive.wrap_for_columns(width, 2, minimum=180, maximum=340, padding=160),
        responsive.wrap_for_columns(width, stage_columns, minimum=180, maximum=320, padding=160),
    )
    if not responsive.remember_layout_key(app, "status_tab", layout_key):
        return
    responsive.apply_card_grid(app._setup_card_grid, app._setup_cards, columns=layout_key[0])
    responsive.apply_card_grid(app._counter_card_grid, app._counter_cards, columns=layout_key[1])
    responsive.apply_card_grid(app._database_card_grid, app._database_cards, columns=layout_key[2])
    responsive.apply_card_grid(app._route_card_grid, app._route_cards, columns=layout_key[3])
    responsive.apply_card_grid(app._stage_card_grid, app._stage_cards, columns=layout_key[4])
    for label in app._route_labels.values():
        responsive.set_wrap(label, layout_key[5])
    for label in app._database_labels.values():
        responsive.set_wrap(label, layout_key[5])
    for label in app._stage_detail_labels:
        responsive.set_wrap(label, layout_key[6])


def _attribute_name(label: str) -> str:
    return {
        "Input Folder": "_input_entry",
        "Artifact Folder": "_artifact_entry",
        "Database Storage Folder": "_corpus_entry",
        "Selected Database": "_selected_db_entry",
        "Semantic Release": "_release_entry",
    }[label]
