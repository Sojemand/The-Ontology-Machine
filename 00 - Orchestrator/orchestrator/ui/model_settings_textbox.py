"""Selectable text widget used by the Orchestrator model settings UI."""

from __future__ import annotations

import math

from . import theme
from .model_settings_widget_utils import (
    coerce_widget_height,
    coerce_widget_width,
    display_line_count,
    font_size,
    line_info,
    widget_exists,
)


def _ctk():
    from . import model_settings_widgets

    return model_settings_widgets.ctk


class SelectableTextBox:
    def __init__(self, parent, text: str, *, font=None, text_color=None) -> None:
        ctk = _ctk()
        self._text = str(text or "")
        self._font = font or theme.font_small()
        self._text_color = text_color or theme.COLOR_MUTED
        self._wraplength = 320
        self._destroyed = False
        self._widget = ctk.CTkTextbox(
            parent,
            width=self._widget_width(),
            height=24,
            font=self._font,
            text_color=self._text_color,
            wrap="word",
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
            border_spacing=0,
            activate_scrollbars=False,
        )
        self._widget.bind("<Destroy>", lambda _event: self._on_destroy())
        self._render()

    def pack(self, *args, **kwargs):
        result = self._widget.pack(*args, **kwargs)
        self._resize_to_content()
        return result

    def grid(self, *args, **kwargs):
        result = self._widget.grid(*args, **kwargs)
        self._resize_to_content()
        return result

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = str(kwargs.pop("text") or "")
        if "text_color" in kwargs:
            self._text_color = kwargs.pop("text_color")
        if "font" in kwargs:
            self._font = kwargs.pop("font")
        wraplength = kwargs.pop("wraplength", None)
        kwargs.pop("justify", None)
        if wraplength is not None:
            self._wraplength = max(int(wraplength), 120)
        if self._destroyed or not widget_exists(self._widget):
            return
        self._widget.configure(font=self._font, text_color=self._text_color, **kwargs)
        self._render()

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "wraplength":
            return self._wraplength
        if key == "font":
            return self._font
        if key == "text_color":
            return self._text_color
        if self._destroyed or not widget_exists(self._widget):
            return None
        return self._widget.cget(key)

    def __getattr__(self, name: str):
        return getattr(self._widget, name)

    def _render(self) -> None:
        if self._destroyed or not widget_exists(self._widget):
            return
        self._widget.configure(width=self._widget_width())
        self._widget.configure(state="normal")
        self._widget.delete("1.0", "end")
        if self._text:
            self._widget.insert("1.0", self._text)
        self._resize_to_content()
        self._widget.configure(state="disabled")

    def _on_destroy(self) -> None:
        self._destroyed = True

    def _resize_to_content(self) -> None:
        if self._destroyed or not widget_exists(self._widget):
            return
        height = self._measured_height() or self._estimated_height()
        width = self._widget_width()
        if coerce_widget_height(self._widget) == height and coerce_widget_width(self._widget) == width:
            return
        self._widget.configure(width=width, height=height)

    def _measured_height(self) -> int:
        update = getattr(self._widget, "update_idletasks", None)
        if callable(update):
            try:
                update()
            except Exception:
                return 0
        display_lines = display_line_count(self._widget, has_text=bool(self._text))
        if not display_lines:
            return 0
        first_line = line_info(self._widget, "1.0")
        line_height = int(first_line[3]) if first_line is not None else max(int(font_size(self._font) * 1.7), 18)
        top = max(int(first_line[1]), 0) if first_line is not None else 3
        measured = (display_lines * line_height) + (top * 2) + 2
        return max(measured, line_height + 6)

    def _estimated_height(self) -> int:
        size = font_size(self._font)
        line_height = max(int(size * 1.7), 18)
        avg_char_width = max(int(size * 0.62), 6)
        chars_per_line = max(self._wraplength // avg_char_width, 12)
        lines = 0
        for raw_line in (self._text.splitlines() or [""]):
            lines += max(1, math.ceil(len(raw_line) / chars_per_line))
        return max((lines * line_height) + 6, line_height + 6)

    def _widget_width(self) -> int:
        return max(self._wraplength + 12, 160)
