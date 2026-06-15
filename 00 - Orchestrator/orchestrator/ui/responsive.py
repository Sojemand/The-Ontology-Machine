"""Responsive window and card-layout helpers for the Orchestrator UI."""

from __future__ import annotations

import customtkinter as ctk

from . import theme

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 820


def fit_window_geometry(
    app,
    *,
    preferred_width: int = DEFAULT_WINDOW_WIDTH,
    preferred_height: int = DEFAULT_WINDOW_HEIGHT,
    margin: int = 72,
) -> str:
    screen_width = _screen_value(app, "winfo_screenwidth", preferred_width + margin)
    screen_height = _screen_value(app, "winfo_screenheight", preferred_height + margin)
    width = max(theme.WINDOW_MIN_WIDTH, min(preferred_width, screen_width - margin))
    height = max(theme.WINDOW_MIN_HEIGHT, min(preferred_height, screen_height - margin))
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 3, 0)
    return f"{width}x{height}+{x}+{y}"


def activate_resize(app) -> None:
    if getattr(app, "_responsive_resize_active", False):
        return
    app._responsive_resize_active = True
    app._responsive_callbacks = {}
    app._responsive_layout_keys = {}
    app._responsive_pending = False

    def _schedule(_event=None) -> None:
        app._responsive_last_width = current_width(app)
        if app._responsive_pending:
            return
        app._responsive_pending = True
        if hasattr(app, "after_idle"):
            app.after_idle(lambda: _dispatch(app))
        elif hasattr(app, "after"):
            app.after(0, lambda: _dispatch(app))
        else:
            _dispatch(app)

    if hasattr(app, "bind"):
        app.bind("<Configure>", _schedule)
    _schedule()


def register_resize_callback(app, key: str, callback) -> None:
    activate_resize(app)
    app._responsive_callbacks[key] = callback
    callback(current_width(app))


def remember_layout_key(app, key: str, value) -> bool:
    activate_resize(app)
    previous = app._responsive_layout_keys.get(key)
    if previous == value:
        return False
    app._responsive_layout_keys[key] = value
    return True


def current_width(app) -> int:
    if hasattr(app, "winfo_width"):
        try:
            width = int(app.winfo_width())
        except Exception:
            width = 0
        if width > 1:
            return width
    return int(getattr(app, "_responsive_last_width", DEFAULT_WINDOW_WIDTH) or DEFAULT_WINDOW_WIDTH)


def columns_for(width: int, *, compact: int = 860, wide: int = 1180, maximum: int = 3) -> int:
    if maximum < 2 or width < compact:
        return 1
    if maximum < 3 or width < wide:
        return 2
    return 3


def apply_card_grid(container, cards: list[object], *, columns: int, padx: int = 6, pady: int = 6) -> bool:
    if not cards:
        return False
    previous = int(getattr(container, "_responsive_columns", 0) or 0)
    if previous == columns:
        return False
    for card in cards:
        if hasattr(card, "grid_forget"):
            card.grid_forget()
    for index, card in enumerate(cards):
        row, column = divmod(index, columns)
        card.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)
    if hasattr(container, "grid_columnconfigure"):
        for column in range(max(previous, columns)):
            container.grid_columnconfigure(column, weight=1 if column < columns else 0)
    container._responsive_columns = columns
    return True


def make_scroll_body(parent, *, height: int | None = None, fill: str = "both", expand: bool = True):
    kwargs = {"fg_color": "transparent"}
    if height is not None:
        kwargs["height"] = height
    body = getattr(ctk, "CTkScrollableFrame", ctk.CTkFrame)(parent, **kwargs)
    body.pack(fill=fill, expand=expand, padx=theme.PADDING, pady=(theme.PADDING_SMALL, theme.PADDING))
    return body


def wrap_for_columns(width: int, columns: int, *, minimum: int = 180, maximum: int = 460, padding: int = 120) -> int:
    available = max(width - padding, minimum)
    return max(minimum, min(maximum, available // max(columns, 1)))


def set_wrap(label, value: int) -> bool:
    if label is None or not hasattr(label, "configure"):
        return False
    wrap = max(int(value), 120)
    if int(getattr(label, "_responsive_wraplength", 0) or 0) == wrap:
        return False
    label._responsive_wraplength = wrap
    label.configure(wraplength=wrap)
    return True


def _dispatch(app) -> None:
    app._responsive_pending = False
    width = current_width(app)
    for callback in list(getattr(app, "_responsive_callbacks", {}).values()):
        callback(width)


def _screen_value(app, method_name: str, fallback: int) -> int:
    if hasattr(app, method_name):
        try:
            value = int(getattr(app, method_name)())
        except Exception:
            value = 0
        if value > 0:
            return value
    return fallback
