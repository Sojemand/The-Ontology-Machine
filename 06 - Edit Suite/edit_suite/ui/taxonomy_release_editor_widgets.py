"""Small widget value helpers for the taxonomy release editor."""

from __future__ import annotations

from typing import Any


def _textbox_value(widget) -> str:
    return str(widget.get("1.0", "end")).strip()


def _replace_entry(widget, value: Any) -> None:
    widget.delete(0, "end")
    widget.insert(0, "" if value is None else str(value))


def _replace_text(widget, value: Any) -> None:
    widget.delete("1.0", "end")
    widget.insert("1.0", "" if value is None else str(value))
