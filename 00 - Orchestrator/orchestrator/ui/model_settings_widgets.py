"""Compatibility facade for Orchestrator model settings widgets."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .model_settings_selector import ScrollableModelSelector
from .model_settings_textbox import SelectableTextBox
from .model_settings_widget_utils import (
    bind_listbox_wheel,
    bind_popup_focus,
    coerce_event_int,
    coerce_widget_height,
    coerce_widget_width,
    display_line_count,
    focus_widget,
    font_size,
    line_info,
    scroll_listbox_wheel,
    widget_exists,
)

__all__ = [
    "SelectableTextBox",
    "ScrollableModelSelector",
    "bind_listbox_wheel",
    "bind_popup_focus",
    "coerce_event_int",
    "coerce_widget_height",
    "coerce_widget_width",
    "ctk",
    "display_line_count",
    "focus_widget",
    "font_size",
    "line_info",
    "scroll_listbox_wheel",
    "tk",
    "widget_exists",
]
