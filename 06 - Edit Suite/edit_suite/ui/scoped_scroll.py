"""Scrollable-frame wrapper that only reacts for the hovered scroll target."""

from __future__ import annotations

import tkinter

import customtkinter as ctk

_WIDGET_SCROLL_CLASSES = {"Canvas", "Listbox", "Text", "Treeview"}


class ScopedScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        setattr(self._parent_canvas, "_edit_suite_scroll_canvas", True)

    def _mouse_wheel_all(self, event) -> None:
        widget = getattr(event, "widget", None)
        if _nearest_scroll_canvas(widget) is not self._parent_canvas:
            return
        if _widget_has_native_scroll(widget, stop=self._parent_canvas):
            return
        super()._mouse_wheel_all(event)


def _nearest_scroll_canvas(widget):
    current = widget
    while current is not None:
        if getattr(current, "_edit_suite_scroll_canvas", False):
            return current
        current = getattr(current, "master", None)
    return None


def _widget_has_native_scroll(widget, *, stop) -> bool:
    current = widget
    while current is not None and current is not stop:
        if _supports_native_scroll(current):
            return True
        current = getattr(current, "master", None)
    return False


def _supports_native_scroll(widget) -> bool:
    if isinstance(widget, tkinter.Text):
        return True
    if widget.__class__.__name__ in _WIDGET_SCROLL_CLASSES:
        return True
    return callable(getattr(widget, "yview", None)) and not getattr(widget, "_edit_suite_scroll_canvas", False)
