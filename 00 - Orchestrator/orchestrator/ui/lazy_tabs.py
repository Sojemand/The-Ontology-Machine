"""Lazy tab registration and activation for the orchestrator UI."""

from __future__ import annotations

STATUS_TAB = "Status"
DEBUG_TAB = "Debug"
CREDENTIALS_TAB = "Credentials"
MODELS_TAB = "Models"
LOG_TAB = "Log"
TAB_ORDER = (STATUS_TAB, DEBUG_TAB, CREDENTIALS_TAB, MODELS_TAB, LOG_TAB)


def configure(app) -> None:
    if hasattr(app, "_tab_builders"):
        return
    app._tab_frames = {}
    app._tab_builders = {}
    app._built_tabs = set()
    app._active_tab_name = ""


def register_tab(app, name: str, builder) -> object:
    configure(app)
    frame = app._tabs.add(name)
    app._tab_frames[name] = frame
    app._tab_builders[name] = builder
    return frame


def build_tab(app, name: str) -> object:
    configure(app)
    frame = app._tab_frames[name]
    if name in app._built_tabs:
        return frame
    app._tab_builders[name](app, frame)
    app._built_tabs.add(name)
    return frame


def activate_initial_tab(app, name: str = STATUS_TAB) -> None:
    build_tab(app, name)
    app._tabs.set(name)
    app._active_tab_name = name


def on_tab_selected(app) -> None:
    configure(app)
    current = _selected_name(app)
    if not current:
        return
    previous = getattr(app, "_active_tab_name", "")
    if previous and previous != current and hasattr(app, "_flush_pending_saves"):
        app._flush_pending_saves()
    build_tab(app, current)
    app._active_tab_name = current


def is_built(app, name: str) -> bool:
    return name in getattr(app, "_built_tabs", set())


def _selected_name(app) -> str:
    tabs = getattr(app, "_tabs", None)
    if tabs is None or not hasattr(tabs, "get"):
        return ""
    try:
        return str(tabs.get() or "").strip()
    except Exception:
        return ""
