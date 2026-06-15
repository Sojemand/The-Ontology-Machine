"""Widget factory helpers for the Orchestrator model settings tab."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from . import model_settings_widgets


def _sync_widget_dependencies() -> None:
    model_settings_widgets.ctk = ctk
    model_settings_widgets.tk = tk


def SelectableTextBox(*args, **kwargs):
    _sync_widget_dependencies()
    return model_settings_widgets.SelectableTextBox(*args, **kwargs)


def ScrollableModelSelector(*args, **kwargs):
    _sync_widget_dependencies()
    return model_settings_widgets.ScrollableModelSelector(*args, **kwargs)


def scroll_listbox_wheel(listbox, event) -> str:
    return model_settings_widgets.scroll_listbox_wheel(listbox, event)
