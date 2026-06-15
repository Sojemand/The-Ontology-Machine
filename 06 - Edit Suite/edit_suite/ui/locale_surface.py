"""Shared helpers for locale-aware Edit Suite authoring surfaces."""
from __future__ import annotations

import json
from collections.abc import Callable

import customtkinter as ctk

from . import theme
from .slot_hints import render_slot_hint, resolve_descriptor
from .text_widgets import create_readonly_text


def clone_payload(value):
    return json.loads(json.dumps(value))


def initialize_locale_state(
    widget,
    *,
    surface,
    metadata: dict[str, object],
    surface_name: str,
    load_payload: Callable[[object, dict[str, object]], None],
) -> None:
    widget._available_locales = [
        str(item) for item in metadata.get("available_locales", []) if str(item).strip()
    ]
    widget._locale_payloads = clone_payload(metadata.get("locale_payloads", {}))
    widget._active_locale = resolve_active_locale(
        surface.draft,
        metadata,
        widget._available_locales,
        surface_name=surface_name,
    )
    if widget._active_locale not in widget._locale_payloads:
        widget._locale_payloads[widget._active_locale] = clone_payload(surface.draft)
    load_payload(
        widget,
        clone_payload(widget._locale_payloads.get(widget._active_locale, surface.draft)),
    )


def render_locale_bar(
    parent,
    *,
    row: int,
    columnspan: int,
    active_locale: str,
    available_locales: list[str],
    slot_descriptors: dict[str, object],
    on_switch: Callable[[str], None],
):
    locale_bar = ctk.CTkFrame(parent)
    locale_bar.grid(
        row=row,
        column=0,
        columnspan=columnspan,
        padx=theme.PADDING_SMALL,
        pady=(theme.PADDING_SMALL, 0),
        sticky="we",
    )
    locale_bar.grid_columnconfigure(1, weight=1)
    create_readonly_text(
        locale_bar,
        text="active_locale",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
    ).grid(row=0, column=0, padx=(0, theme.PADDING_SMALL), pady=(0, 2), sticky="w")
    locale_values = available_locales or [active_locale or ""]
    locale_widget = ctk.CTkOptionMenu(locale_bar, values=locale_values)
    locale_widget.set(active_locale or locale_values[0])
    locale_widget.configure(command=on_switch)
    locale_widget.grid(row=0, column=1, sticky="w")
    render_slot_hint(
        locale_bar,
        resolve_descriptor(slot_descriptors, "active_locale"),
        row=1,
        column=0,
    )
    return locale_widget


def switch_locale(
    widget,
    locale: str,
    *,
    surface_name: str,
    sync_current: Callable[[object], None],
    build_payload: Callable[[], dict[str, object]],
    load_payload: Callable[[object, dict[str, object]], None],
    empty_payload: Callable[[str], dict[str, object]],
) -> bool:
    locale = str(locale).strip()
    current_locale = active_locale(widget, surface_name=surface_name)
    if not locale or locale == current_locale:
        return False
    sync_current(widget)
    widget._locale_payloads[current_locale] = clone_payload(build_payload())
    widget._active_locale = locale
    load_payload(
        widget,
        clone_payload(widget._locale_payloads.get(locale, empty_payload(locale))),
    )
    return True


def active_locale(widget, *, surface_name: str) -> str:
    locale = str(getattr(widget, "_active_locale", "")).strip()
    if not locale:
        raise ValueError(f"{surface_name} surface does not contain an active_locale.")
    return locale


def resolve_active_locale(
    payload: dict,
    metadata: dict[str, object],
    available_locales: list[str],
    *,
    surface_name: str,
) -> str:
    locale = str(payload.get("active_locale") or metadata.get("active_locale") or "").strip()
    if not locale:
        raise ValueError(
            f"{surface_name} surface must provide an active_locale from the draft or descriptor."
        )
    if locale not in set(available_locales):
        raise ValueError(
            f"{surface_name} surface contains an unknown active_locale: {locale}"
        )
    return locale
