"""Shared readonly text widgets for the Edit Suite UI."""
from __future__ import annotations

import customtkinter as ctk

from . import theme


def create_readonly_text(
    parent,
    *,
    text: str = "",
    font=None,
    text_color=None,
    wrap: str = "word",
    min_lines: int = 1,
    max_lines: int = 6,
    height: int | None = None,
    justify: str = "left",
) -> ctk.CTkTextbox:
    widget = _create_textbox(
        parent,
        height=height or _text_height(text, min_lines=min_lines, max_lines=max_lines),
        wrap=wrap,
        font=font or theme.font_normal(),
        text_color=text_color or theme.COLOR_TEXT,
        blend_with_parent=True,
    )
    set_readonly_text(widget, text, min_lines=min_lines, max_lines=max_lines, height=height, justify=justify)
    return widget


def set_readonly_text(
    widget: ctk.CTkTextbox,
    text: str,
    *,
    min_lines: int = 1,
    max_lines: int = 6,
    height: int | None = None,
    justify: str = "left",
) -> None:
    widget.configure(state="normal", height=height or _text_height(text, min_lines=min_lines, max_lines=max_lines))
    widget.delete("1.0", "end")
    widget.insert("1.0", text)
    _apply_justify(widget, justify=justify)
    widget.configure(state="disabled")


def render_source_label(widget: ctk.CTkTextbox, *, source: str, stale: bool, message: str) -> None:
    suffix = " (stale cache)" if stale else ""
    text = f"Registry source: {source}{suffix}"
    if message:
        text = f"{text}\n{message}"
    set_readonly_text(widget, text, min_lines=2, max_lines=4)


def create_json_textbox(parent, *, height: int = 220) -> ctk.CTkTextbox:
    return _create_textbox(parent, height=height, wrap="word", font=theme.font_mono(), text_color=theme.COLOR_TEXT)


def _create_textbox(parent, *, height: int, wrap: str, font, text_color, blend_with_parent: bool = False) -> ctk.CTkTextbox:
    options = {"height": height, "wrap": wrap, "font": font, "text_color": text_color}
    if blend_with_parent:
        options["fg_color"] = _parent_fg_color(parent)
        options["border_width"] = 0
        options["corner_radius"] = 0
    widget = ctk.CTkTextbox(parent, **options)
    _bind_copy_support(widget)
    return widget


def _bind_copy_support(widget: ctk.CTkTextbox) -> None:
    inner = getattr(widget, "_textbox", widget)
    try:
        inner.configure(cursor="xterm", insertwidth=0, takefocus=True)
    except Exception:
        pass
    handler = _copy_callback(widget)
    inner.bind("<Control-c>", handler, add="+")
    inner.bind("<Control-C>", handler, add="+")


def _copy_callback(widget: ctk.CTkTextbox):
    def handle_copy(event=None):
        del event
        return _copy_selection(widget)

    return handle_copy


def _copy_selection(widget: ctk.CTkTextbox):
    target = getattr(widget, "_textbox", widget)
    try:
        selected_text = target.get("sel.first", "sel.last")
    except Exception:
        return "break"
    widget.clipboard_clear()
    widget.clipboard_append(selected_text)
    return "break"


def _apply_justify(widget: ctk.CTkTextbox, *, justify: str) -> None:
    inner = getattr(widget, "_textbox", None)
    if inner is None:
        return
    inner.tag_configure("content", justify=justify)
    inner.tag_add("content", "1.0", "end")


def _parent_fg_color(parent):
    try:
        return parent.cget("fg_color")
    except Exception:
        return ("gray92", "gray18")


def _text_height(text: str, *, min_lines: int, max_lines: int) -> int:
    line_count = max(1, text.count("\n") + 1)
    bounded_lines = max(min_lines, min(max_lines, line_count))
    return max(theme.INPUT_HEIGHT, 12 + bounded_lines * 18)
