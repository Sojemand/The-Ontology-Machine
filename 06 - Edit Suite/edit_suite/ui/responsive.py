"""Responsive window helpers for the Edit Suite UI."""

from __future__ import annotations

import re

from . import theme

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 820
DEFAULT_MARGIN = 72
_GEOMETRY_RE = re.compile(r"^(?P<width>\d+)x(?P<height>\d+)(?:(?P<x>[+-]\d+)(?P<y>[+-]\d+))?$")


def fit_window_geometry(
    app,
    *,
    preferred_width: int = DEFAULT_WINDOW_WIDTH,
    preferred_height: int = DEFAULT_WINDOW_HEIGHT,
    margin: int = DEFAULT_MARGIN,
) -> str:
    screen_width = _screen_value(app, "winfo_screenwidth", preferred_width + margin)
    screen_height = _screen_value(app, "winfo_screenheight", preferred_height + margin)
    width = max(theme.WINDOW_MIN_WIDTH, min(preferred_width, screen_width - margin))
    height = max(theme.WINDOW_MIN_HEIGHT, min(preferred_height, screen_height - margin))
    return _centered_geometry(screen_width, screen_height, width, height)


def restore_window_geometry(app, saved_geometry: str) -> str:
    match = _GEOMETRY_RE.match(str(saved_geometry or "").strip())
    if match is None:
        return fit_window_geometry(app)
    screen_width = _screen_value(app, "winfo_screenwidth", DEFAULT_WINDOW_WIDTH + DEFAULT_MARGIN)
    screen_height = _screen_value(app, "winfo_screenheight", DEFAULT_WINDOW_HEIGHT + DEFAULT_MARGIN)
    width = max(theme.WINDOW_MIN_WIDTH, min(int(match.group("width")), screen_width - DEFAULT_MARGIN))
    height = max(theme.WINDOW_MIN_HEIGHT, min(int(match.group("height")), screen_height - DEFAULT_MARGIN))
    x = _parse_int(match.group("x"))
    y = _parse_int(match.group("y"))
    if x is None or y is None:
        return _centered_geometry(screen_width, screen_height, width, height)
    if x < 0 or y < 0 or x + width > screen_width or y + height > screen_height:
        return _centered_geometry(screen_width, screen_height, width, height)
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
            return
        if hasattr(app, "after"):
            app.after(0, lambda: _dispatch(app))
            return
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


def _dispatch(app) -> None:
    app._responsive_pending = False
    width = current_width(app)
    for callback in list(getattr(app, "_responsive_callbacks", {}).values()):
        callback(width)


def _centered_geometry(screen_width: int, screen_height: int, width: int, height: int) -> str:
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 3, 0)
    return f"{width}x{height}+{x}+{y}"


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _screen_value(app, method_name: str, fallback: int) -> int:
    if hasattr(app, method_name):
        try:
            value = int(getattr(app, method_name)())
        except Exception:
            value = 0
        if value > 0:
            return value
    return fallback
