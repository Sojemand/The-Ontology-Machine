"""Dismissible artifact-list helpers for the debug-host UI."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import customtkinter as ctk

from . import theme


def visible_entries(app, entries: list[object]) -> list[object]:
    hidden = _hidden_paths(app)
    return [entry for entry in entries if str(getattr(entry, "path", "")) not in hidden]


def dismiss_path(app, path: Path | str) -> None:
    hidden = set(_hidden_paths(app))
    hidden.add(str(Path(path)))
    setattr(app, "_hidden_debug_artifact_paths", hidden)


def reset_hidden_paths(app) -> None:
    setattr(app, "_hidden_debug_artifact_paths", set())


def restore_hidden_paths(app, values: object) -> None:
    hidden: set[str] = set()
    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        for value in values:
            text = str(value or "").strip()
            if text:
                hidden.add(str(Path(text)))
    setattr(app, "_hidden_debug_artifact_paths", hidden)


def persisted_hidden_paths(app) -> list[str]:
    return sorted(_hidden_paths(app))


def render_entries(app, entries: list[object], *, selected_index: int) -> None:
    frame = getattr(app, "_debug_artifact_buttons_frame", None)
    if frame is None or not hasattr(frame, "winfo_children") or not hasattr(frame, "tk"):
        return
    for child in list(frame.winfo_children()):
        child.destroy()
    rows: list[object] = []
    for index, entry in enumerate(entries):
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(0, 6))
        button = ctk.CTkButton(
            row,
            text=getattr(entry, "label", ""),
            anchor="w",
            height=theme.BUTTON_HEIGHT,
            command=lambda index=index: app._select_debug_artifact(index),
            fg_color=theme.COLOR_ACCENT if selected_index == index else "transparent",
            text_color=theme.COLOR_TEXT,
            hover_color=theme.COLOR_ACCENT,
        )
        button.pack(side="left", fill="x", expand=True)
        remove = ctk.CTkButton(
            row,
            text="X",
            width=34,
            height=theme.BUTTON_HEIGHT,
            command=lambda path=getattr(entry, "path", ""): app._dismiss_debug_artifact(path),
            fg_color="transparent",
            text_color=theme.COLOR_MUTED,
            hover_color=theme.COLOR_ERROR,
        )
        remove.pack(side="left", padx=(6, 0))
        rows.append((row, button, remove))
    setattr(app, "_debug_artifact_buttons", rows)


def _hidden_paths(app) -> set[str]:
    hidden = getattr(app, "_hidden_debug_artifact_paths", None)
    if isinstance(hidden, set):
        return hidden
    hidden = set()
    setattr(app, "_hidden_debug_artifact_paths", hidden)
    return hidden
