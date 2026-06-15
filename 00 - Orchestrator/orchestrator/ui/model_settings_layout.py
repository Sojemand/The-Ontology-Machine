"""Responsive widget construction for the Orchestrator model settings tab."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ..models import provider_definition, provider_display_names, provider_id_for_display_name, provider_note
from . import model_catalog_actions, responsive, theme
from . import model_settings_widget_factory as widget_factory

_PROVIDER_CARD_SPECS = (
    ("llm_shared", "LLM Provider"),
    ("optimizer_ocr", "Optimizer OCR Provider"),
    ("embeddings", "Embedding Provider"),
)
_CARD_SPECS = (
    ("interpreter", "Interpreter", True, False),
    ("normalizer", "Normalizer", True, False),
    ("optimizer_ocr", "Optimizer OCR", True, True),
    ("corpus_builder_embeddings", "Corpus Builder Embeddings", False, False),
)


def build_model_settings_tab(app, parent) -> None:
    app._runtime_settings_widgets = {}
    app._provider_runtime_widgets = {}
    app._model_catalog_group_labels = {}
    app._model_wrap_labels = []
    app._models_scroll_body = responsive.make_scroll_body(parent)
    body = app._models_scroll_body
    _wrap_label(app, body, "Models", font=theme.font_header(), text_color=theme.COLOR_TEXT).pack(anchor="w")
    _wrap_label(app, body, "The Orchestrator is the only productive editing point for non-secret model and provider parameters. Thinking remains fixed to no thinking and is not editable.").pack(anchor="w", pady=(4, 0))
    header = ctk.CTkFrame(body, fg_color="transparent")
    header.pack(fill="x", pady=(theme.PADDING_SMALL, 0))
    app._model_catalog_refresh_button = ctk.CTkButton(header, text="Refresh Models", width=150, height=theme.BUTTON_HEIGHT, command=lambda: model_catalog_actions.start_model_catalog_refresh(app))
    app._model_catalog_refresh_button.pack(side="right")
    app._runtime_settings_notice_label = _wrap_label(app, body, "Changes are saved directly under state/runtime_settings.json.")
    app._runtime_settings_notice_label.pack(anchor="w", pady=(4, 0))
    app._model_catalog_notice_label = _wrap_label(app, body, "")
    app._model_catalog_notice_label.pack(anchor="w", pady=(4, 0))
    for target in ("llm_shared", "optimizer_ocr", "embeddings"):
        label = _wrap_label(app, body, "")
        label.pack(anchor="w", pady=(2, 0))
        app._model_catalog_group_labels[target] = label
    app._provider_cards_grid = ctk.CTkFrame(body, fg_color="transparent")
    app._provider_cards_grid.pack(fill="x", pady=(theme.PADDING_SMALL, 0))
    app._provider_cards = []
    for key, title in _PROVIDER_CARD_SPECS:
        card = ctk.CTkFrame(app._provider_cards_grid)
        app._provider_cards.append(card)
        app._provider_runtime_widgets[key] = _build_provider_card(app, card, target=key, title=title)
    app._model_cards_grid = ctk.CTkFrame(body, fg_color="transparent")
    app._model_cards_grid.pack(fill="both", expand=True, pady=(theme.PADDING_SMALL, 0))
    app._model_cards = []
    for key, title, include_tokens, include_timeout in _CARD_SPECS:
        card = ctk.CTkFrame(app._model_cards_grid)
        app._model_cards.append(card)
        app._runtime_settings_widgets[key] = _build_card(
            app,
            card,
            title=title,
            include_tokens=include_tokens,
            include_timeout=include_timeout,
        )
    responsive.register_resize_callback(app, "model_settings_tab", lambda width: _apply_layout(app, width))
    model_catalog_actions.initialize_model_catalog(app)


def _build_card(app, parent, *, title: str, include_tokens: bool, include_timeout: bool = False) -> dict[str, object]:
    ctk.CTkLabel(parent, text=title, font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    ctk.CTkLabel(
        parent,
        text="LLM model, max_output_tokens, and timeout_seconds" if include_timeout else "LLM model and max_output_tokens" if include_tokens else "Embedding model",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
    ).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 0))
    fields: dict[str, object] = {"model": _build_model_row(app, parent, label="Model")}
    if include_tokens:
        fields["max_output_tokens"] = _build_entry_row(app, parent, label="Max Output Tokens")
    if include_timeout:
        fields["timeout_seconds"] = _build_entry_row(app, parent, label="Timeout Seconds")
    fields["model_status"] = _wrap_label(app, parent, "")
    fields["model_status"].pack(anchor="w", padx=theme.PADDING_SMALL, pady=(0, 10))
    return fields


def _build_provider_card(app, parent, *, target: str, title: str) -> dict[str, object]:
    ctk.CTkLabel(parent, text=title, font=theme.font_normal()).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(10, 0))
    ctk.CTkLabel(parent, text="Provider preset with native or OpenAI-compatible base URL", font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(2, 0))
    fields: dict[str, object] = {
        "provider": _build_provider_row(app, parent, target=target, label="Provider"),
        "base_url": _build_entry_row(app, parent, label="Base URL", on_change=lambda: _apply_provider_settings_change(app)),
        "note": _wrap_label(app, parent, ""),
    }
    fields["note"].pack(anchor="w", padx=theme.PADDING_SMALL, pady=(0, 10))
    return fields


def _build_model_row(app, parent, *, label: str):
    ctk.CTkLabel(parent, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    selector = _ScrollableModelSelector(parent, values=["Loading models..."], command=lambda _value: _apply_runtime_change(app))
    selector.pack(fill="x", padx=theme.PADDING_SMALL, pady=(4, 6))
    if hasattr(selector, "bind"):
        selector.bind("<KeyRelease>", lambda _event: _apply_runtime_change(app))
        selector.bind("<FocusOut>", lambda _event: app._flush_pending_save("runtime_settings"))
    return selector


def _build_provider_row(app, parent, *, target: str, label: str):
    ctk.CTkLabel(parent, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    selector = ctk.CTkOptionMenu(
        parent,
        height=theme.INPUT_HEIGHT,
        values=list(provider_display_names(target)),
        command=lambda value: _apply_provider_preset_change(app, target, value),
    )
    selector.pack(fill="x", padx=theme.PADDING_SMALL, pady=(4, 6))
    if hasattr(selector, "bind"):
        selector.bind("<FocusOut>", lambda _event: app._flush_pending_save("runtime_settings"))
    return selector


def _build_entry_row(app, parent, *, label: str, on_change=None):
    ctk.CTkLabel(parent, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).pack(anchor="w", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 0))
    entry = ctk.CTkEntry(parent, height=theme.INPUT_HEIGHT)
    entry.pack(fill="x", padx=theme.PADDING_SMALL, pady=(4, 10))
    callback = on_change or (lambda: _apply_runtime_change(app))
    entry.bind("<KeyRelease>", lambda _event: callback())
    entry.bind("<FocusOut>", lambda _event: app._flush_pending_save("runtime_settings"))
    return entry


def _apply_runtime_change(app) -> None:
    _refresh_provider_notes(app)
    app._on_runtime_settings_change()
    app._update_button_state()


def _apply_provider_settings_change(app) -> None:
    _refresh_provider_notes(app)
    model_catalog_actions.render_model_catalog(app)
    app._on_runtime_settings_change()
    app._update_button_state()


def _apply_provider_preset_change(app, target: str, value: str) -> None:
    selected = str(value or "").strip()
    definition = provider_definition(provider_id_for_display_name(selected, target=target))
    default_url = definition.default_base_url
    if default_url:
        widgets = getattr(app, "_provider_runtime_widgets", {}).get(target, {})
        base_url_widget = widgets.get("base_url")
        if base_url_widget is not None:
            _set_text(base_url_widget, default_url)
    _apply_provider_settings_change(app)


def _refresh_provider_notes(app) -> None:
    for target, widgets in getattr(app, "_provider_runtime_widgets", {}).items():
        selected = str(getattr(widgets.get("provider"), "get", lambda: "")() or "").strip()
        provider_id = provider_id_for_display_name(selected, target=target)
        note_widget = widgets.get("note")
        if note_widget is not None:
            note_widget.configure(text=provider_note(provider_id))


def _apply_layout(app, width: int) -> None:
    columns = responsive.columns_for(width, compact=940, wide=1180, maximum=2)
    wrap = responsive.wrap_for_columns(width, columns, minimum=220, maximum=520, padding=220)
    if not responsive.remember_layout_key(app, "model_settings_tab", (columns, wrap)):
        return
    responsive.apply_card_grid(app._provider_cards_grid, app._provider_cards, columns=columns)
    responsive.apply_card_grid(app._model_cards_grid, app._model_cards, columns=columns)
    for label in getattr(app, "_model_wrap_labels", []):
        responsive.set_wrap(label, wrap)


def _wrap_label(app, parent, text: str, *, font=None, text_color=None):
    label = _SelectableTextBox(parent, text, font=font or theme.font_small(), text_color=text_color or theme.COLOR_MUTED)
    getattr(app, "_model_wrap_labels").append(label)
    return label


def _sync_widget_dependencies() -> None:
    widget_factory.ctk = ctk
    widget_factory.tk = tk


def _SelectableTextBox(*args, **kwargs):
    _sync_widget_dependencies()
    return widget_factory.SelectableTextBox(*args, **kwargs)


def _ScrollableModelSelector(*args, **kwargs):
    _sync_widget_dependencies()
    return widget_factory.ScrollableModelSelector(*args, **kwargs)


def _scroll_listbox_wheel(listbox, event) -> str:
    _sync_widget_dependencies()
    return widget_factory.scroll_listbox_wheel(listbox, event)


def _set_text(widget, value: str) -> None:
    if hasattr(widget, "set"):
        widget.set(value)
        return
    widget.delete(0, "end")
    if value:
        widget.insert(0, value)
