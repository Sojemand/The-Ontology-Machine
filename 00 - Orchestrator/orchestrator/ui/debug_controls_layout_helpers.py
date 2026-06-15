"""Reusable row and grid helpers for the debug console layout."""

from __future__ import annotations

import customtkinter as ctk

from . import theme


def card(parent, title: str):
    panel = ctk.CTkFrame(parent)
    ctk.CTkLabel(panel, text=title, font=theme.font_normal(), text_color=theme.COLOR_TEXT).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    return panel


def field_row(app, parent, label: str, attr_name: str, *, control=None, button_text: str = "", button_command=None):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(row, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w")
    field = ctk.CTkFrame(row, fg_color="transparent")
    field.pack(fill="x")
    widget = control or ctk.CTkEntry(field, height=theme.INPUT_HEIGHT)
    widget.pack(side="left", fill="x", expand=True)
    if button_text and button_command is not None:
        ctk.CTkButton(field, text=button_text, width=88, command=button_command).pack(side="left", padx=(6, 0))
    if hasattr(widget, "bind"):
        widget.bind("<KeyRelease>", lambda _event: app._on_debug_change())
        widget.bind("<FocusOut>", lambda _event: app._flush_pending_save("debug_state"))
    setattr(app, attr_name, widget)
    return row


def option_menu_row(app, parent, label: str, attr_name: str, *, variable, values: list[str]):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(row, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w")
    field = ctk.CTkFrame(row, fg_color="transparent")
    field.pack(fill="x")
    widget = ctk.CTkOptionMenu(
        field,
        variable=variable,
        values=values,
        command=lambda _value: app._on_debug_change(),
    )
    widget.pack(side="left", fill="x", expand=True)
    if hasattr(widget, "bind"):
        widget.bind("<FocusOut>", lambda _event: app._flush_pending_save("debug_state"))
    setattr(app, attr_name, widget)
    return row


def hash_row(app, parent):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._debug_hash_check = ctk.CTkCheckBox(row, text="Processed Hashes", variable=app._debug_hash_var, command=app._on_debug_change)
    app._debug_hash_check.pack(anchor="w")
    return row


def check_toggle_row(app, parent):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(row, text="Checks", font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w")
    app._debug_check_free_text_var = ctk.BooleanVar(value=True)
    app._debug_check_context_scalars_var = ctk.BooleanVar(value=True)
    app._debug_check_content_fields_var = ctk.BooleanVar(value=True)
    app._debug_check_rows_var = ctk.BooleanVar(value=True)
    for text, variable in (
        ("Free Text", app._debug_check_free_text_var),
        ("Context Scalars", app._debug_check_context_scalars_var),
        ("Content Fields", app._debug_check_content_fields_var),
        ("Rows", app._debug_check_rows_var),
    ):
        ctk.CTkCheckBox(row, text=text, variable=variable, command=app._on_debug_change).pack(anchor="w")
    return row


def persist_page_images_row(app, parent):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._debug_persist_page_images_check = ctk.CTkCheckBox(
        row,
        text="Persist Page Images in DB",
        variable=app._debug_persist_page_images_var,
        command=app._on_debug_change,
    )
    app._debug_persist_page_images_check.pack(anchor="w")
    return row


def apply_console_grid(container, cards: list[object], *, columns: int) -> None:
    if not cards:
        return
    for panel in cards:
        if hasattr(panel, "grid_forget"):
            panel.grid_forget()
    for index, panel in enumerate(cards):
        row, column = divmod(index, columns)
        panel.grid(row=row, column=column, sticky="new", padx=6, pady=6)
    if hasattr(container, "grid_columnconfigure"):
        for column in range(max(columns, len(cards))):
            container.grid_columnconfigure(column, weight=1 if column < columns else 0)


def set_card_visible(card, visible: bool) -> None:
    setattr(card, "visible", visible)
