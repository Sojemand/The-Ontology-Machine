"""Lazy tab registration for the Edit Suite detail tabs."""

from __future__ import annotations

from ..policy import SECTION_ORDER

TAB_ORDER = tuple(name for name, _label in SECTION_ORDER)


def configure(app) -> None:
    if hasattr(app, "_tab_builders"):
        return
    app._tab_frames = {}
    app._tab_builders = {}
    app._built_tabs = set()
    app._active_tab_name = ""


def register_tab(app, name: str, builder):
    configure(app)
    frame = app._shell["tabs"].add(name)
    app._tab_frames[name] = frame
    app._tab_builders[name] = builder
    return frame


def build_tab(app, name: str):
    configure(app)
    frame = app._tab_frames[name]
    if name in app._built_tabs:
        return frame
    app._tab_builders[name](app, frame)
    app._built_tabs.add(name)
    return frame


def activate(app, name: str) -> None:
    build_tab(app, name)
    app._shell["tabs"].set(name)
    app._active_tab_name = name


def is_built(app, name: str) -> bool:
    return name in getattr(app, "_built_tabs", set())


def selected_name(app) -> str:
    tabs = getattr(app, "_shell", {}).get("tabs")
    if tabs is None or not hasattr(tabs, "get"):
        return ""
    try:
        return str(tabs.get() or "").strip()
    except Exception:
        return ""
