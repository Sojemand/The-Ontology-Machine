"""Responsive widget construction for the Orchestrator credentials tab."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ..credentials import policy
from . import responsive, theme


def build_credentials_tab(app, parent) -> None:
    app._credential_widgets = {}
    app._capability_widgets = {}
    app._credentials_wrap_labels = []
    app._credentials_scroll_body = responsive.make_scroll_body(parent)
    body = app._credentials_scroll_body
    _wrap_label(app, body, "Credentials", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(anchor="w")
    _wrap_label(
        app,
        body,
        "The Orchestrator remains the sole auth owner for shared LLM API keys, Optimizer OCR credentials, OpenAI OAuth, and the separate embeddings key.",
    ).pack(anchor="w", pady=(4, 0))
    app._credentials_notice_label = _wrap_label(app, body, "", text_color=theme.COLOR_WARNING)
    app._credentials_notice_label.pack(anchor="w", pady=(4, 0))
    _build_effective_source_row(app, body)
    app._credentials_secret_grid = ctk.CTkFrame(body, fg_color="transparent")
    app._credentials_secret_grid.pack(fill="x", pady=(theme.PADDING_SMALL, 0))
    app._credential_cards = [
        _build_secret_card(app, app._credentials_secret_grid, target="llm_shared", title="LLM Shared API Key"),
        _build_secret_card(app, app._credentials_secret_grid, target="optimizer_ocr", title="Optimizer OCR API Key"),
        _build_secret_card(app, app._credentials_secret_grid, target="embeddings", title="Embeddings API Key"),
    ]
    _build_oauth_section(app, body)
    _build_capability_preview(app, body)
    responsive.register_resize_callback(app, "credentials_tab", lambda width: _apply_layout(app, width))


def _build_effective_source_row(app, parent) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(theme.PADDING, 0))
    ctk.CTkLabel(row, text="LLM runtime source:", font=theme.font_normal()).pack(side="left")
    app._credentials_mode_label = ctk.CTkLabel(row, text="", font=theme.font_normal(), text_color=theme.COLOR_MUTED)
    app._credentials_mode_label.pack(side="left", padx=(8, 0))
    app._credentials_mode_detail_label = _wrap_label(app, parent, "")
    app._credentials_mode_detail_label.pack(anchor="w", pady=(4, 0))


def _build_secret_card(app, parent, *, target: str, title: str):
    card = ctk.CTkFrame(parent)
    ctk.CTkLabel(card, text=title, font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    entry_row = ctk.CTkFrame(card, fg_color="transparent")
    entry_row.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    entry = ctk.CTkEntry(entry_row, height=theme.INPUT_HEIGHT, show="*")
    _bind_secret_entry_context_menu(entry)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    save_button = ctk.CTkButton(entry_row, text="Save", width=96, height=theme.BUTTON_HEIGHT, command=lambda: app._save_credentials_target(target))
    save_button.pack(side="left", padx=(0, 6))
    delete_button = ctk.CTkButton(entry_row, text="Delete API", width=108, height=theme.BUTTON_HEIGHT, command=lambda: app._delete_credentials_target(target))
    delete_button.pack(side="left")
    presence = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED)
    presence.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(8, 0))
    source = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED)
    source.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 0))
    detail = _wrap_label(app, card, "")
    detail.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 10))
    app._credential_widgets[target] = {"entry": entry, "save": save_button, "delete": delete_button, "presence": presence, "source": source, "detail": detail}
    return card


def _bind_secret_entry_context_menu(entry) -> None:
    bind = getattr(entry, "bind", None)
    if not callable(bind):
        return

    def show_menu(event):
        widget = getattr(event, "widget", entry)
        try:
            widget.focus_set()
            widget.icursor(widget.index(f"@{getattr(event, 'x', 0)}"))
        except Exception:
            pass
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Paste", command=lambda: _generate_entry_event(widget, "<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select all", command=lambda: _select_entry_text(widget))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass
        return "break"

    bind("<Button-3>", show_menu)
    bind("<Button-2>", show_menu)


def _generate_entry_event(widget, event_name: str) -> None:
    event_generate = getattr(widget, "event_generate", None)
    if not callable(event_generate):
        return
    try:
        event_generate(event_name)
    except Exception:
        return


def _select_entry_text(widget) -> None:
    try:
        widget.focus_set()
        widget.selection_range(0, "end")
        widget.icursor("end")
    except Exception:
        return


def _build_oauth_section(app, parent) -> None:
    card = ctk.CTkFrame(parent)
    card.pack(fill="x", pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(card, text="OpenAI OAuth Login", font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    app._oauth_status_label = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED)
    app._oauth_status_label.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(8, 0))
    app._oauth_account_label = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED)
    app._oauth_account_label.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 0))
    app._oauth_message_label = _wrap_label(app, card, "")
    app._oauth_message_label.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 0))
    buttons = ctk.CTkFrame(card, fg_color="transparent")
    buttons.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    app._oauth_login_btn = ctk.CTkButton(buttons, text="Login", width=96, height=theme.BUTTON_HEIGHT, command=app._login_oauth)
    app._oauth_login_btn.pack(side="left", padx=(0, 6))
    app._oauth_logout_btn = ctk.CTkButton(buttons, text="Logout", width=96, height=theme.BUTTON_HEIGHT, command=app._logout_oauth)
    app._oauth_logout_btn.pack(side="left")
    app._oauth_info_label = _wrap_label(app, card, "OpenAI OAuth only affects OpenAI LLM runtime paths, including Optimizer OCR. Other providers and embeddings remain configured separately through API keys.")
    app._oauth_info_label.pack(anchor="w", padx=theme.PADDING_SMALL, pady=(8, 10))


def _build_capability_preview(app, parent) -> None:
    card = ctk.CTkFrame(parent)
    card.pack(fill="both", expand=True, pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(card, text="Capability Preview", font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    grid = ctk.CTkFrame(card, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    for column, text in enumerate(("Module", "Status", "Detail")):
        grid.grid_columnconfigure(column, weight=1 if column != 1 else 0)
        ctk.CTkLabel(grid, text=text, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(row=0, column=column, sticky="w", padx=4, pady=(0, 6))
    for row, (module_key, display_name, _target, operation) in enumerate(policy.CAPABILITY_SPECS, start=1):
        ctk.CTkLabel(grid, text=display_name, font=theme.font_normal()).grid(row=row, column=0, sticky="w", padx=4, pady=4)
        status = ctk.CTkLabel(grid, text="", font=theme.font_small())
        status.grid(row=row, column=1, sticky="w", padx=4, pady=4)
        detail = _wrap_label(app, grid, "")
        detail.grid(row=row, column=2, sticky="w", padx=4, pady=4)
        app._capability_widgets[(module_key, operation)] = {"status": status, "detail": detail}


def _apply_layout(app, width: int) -> None:
    columns = responsive.columns_for(width, compact=940, wide=1180, maximum=2)
    wrap = responsive.wrap_for_columns(width, columns, minimum=220, maximum=620, padding=220)
    if not responsive.remember_layout_key(app, "credentials_tab", (columns, wrap)):
        return
    responsive.apply_card_grid(app._credentials_secret_grid, app._credential_cards, columns=columns)
    for label in getattr(app, "_credentials_wrap_labels", []):
        responsive.set_wrap(label, wrap)


def _wrap_label(app, parent, text: str, *, font=None, text_color=None):
    label = ctk.CTkLabel(parent, text=text, font=font or theme.font_small(), text_color=text_color or theme.COLOR_MUTED, justify="left")
    getattr(app, "_credentials_wrap_labels").append(label)
    return label
