"""Shared CustomTkinter theme for the Vision Pipeline GUIs."""
from __future__ import annotations

import customtkinter as ctk

APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"

WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 720
INPUT_HEIGHT = 34
BUTTON_HEIGHT = 38
ACTION_BUTTON_HEIGHT = 42

FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_HEADER = 16
FONT_SIZE_MONO = 11

PADDING = 12
PADDING_SMALL = 6
PADDING_LARGE = 20

COLOR_TEXT = ("gray10", "gray90")
COLOR_WARNING = "#FFA500"
COLOR_SUCCESS = "#00CC66"
COLOR_ERROR = "#FF4444"
COLOR_MUTED = "#888888"
COLOR_ACCENT = "#3B8ED0"

STATUS_READY = "Ready"
STATUS_DONE = "Done"
STATUS_ERROR = "Error"


def apply_theme() -> None:
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)


def font_normal():
    return (FONT_FAMILY, FONT_SIZE_NORMAL)


def font_small():
    return (FONT_FAMILY, FONT_SIZE_SMALL)


def font_header():
    return (FONT_FAMILY, FONT_SIZE_HEADER, "bold")


def font_mono():
    return ("Consolas", FONT_SIZE_MONO)
