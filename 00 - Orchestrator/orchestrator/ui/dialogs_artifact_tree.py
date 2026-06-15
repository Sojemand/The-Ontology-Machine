"""Artifact-tree creation dialog."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from . import theme
from .dialogs_basic import show_error


def prompt_create_artifact_tree(
    app,
    *,
    initial_parent: str,
    initial_name: str,
) -> dict[str, str] | None:
    window = ctk.CTkToplevel(app)
    window.title("Create Artifact Tree")
    window.geometry("620x300")
    window.minsize(560, 280)
    if hasattr(window, "transient"):
        window.transient(app)
    if hasattr(window, "grab_set"):
        window.grab_set()

    result: dict[str, str] | None = None
    parent_var = ctk.StringVar(value=initial_parent)
    name_var = ctk.StringVar(value=initial_name or "Artifact Tree")

    root = ctk.CTkFrame(window)
    root.pack(fill="both", expand=True, padx=theme.PADDING, pady=theme.PADDING)
    ctk.CTkLabel(root, text="Create Artifact Tree", font=theme.font_header(), text_color=theme.COLOR_TEXT, anchor="w").pack(fill="x")
    ctk.CTkLabel(
        root,
        text="Create the canonical tree and automatically set input, artifacts, corpus storage, and the default DB to the matching paths.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        justify="left",
        wraplength=560,
    ).pack(fill="x", pady=(4, theme.PADDING_SMALL))

    form = ctk.CTkFrame(root, fg_color="transparent")
    form.pack(fill="x")
    ctk.CTkLabel(form, text="Parent folder", font=theme.font_normal()).pack(anchor="w")
    parent_row = ctk.CTkFrame(form, fg_color="transparent")
    parent_row.pack(fill="x", pady=(4, theme.PADDING_SMALL))
    parent_entry = ctk.CTkEntry(parent_row, textvariable=parent_var, height=theme.INPUT_HEIGHT)
    parent_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ctk.CTkButton(parent_row, text="Select", width=90, height=theme.BUTTON_HEIGHT, command=lambda: _browse_parent(window, parent_var)).pack(side="left")
    ctk.CTkLabel(form, text="Tree name", font=theme.font_normal()).pack(anchor="w")
    name_entry = ctk.CTkEntry(form, textvariable=name_var, height=theme.INPUT_HEIGHT)
    name_entry.pack(fill="x", pady=(4, 0))

    actions = ctk.CTkFrame(root, fg_color="transparent")
    actions.pack(fill="x", pady=(theme.PADDING, 0))

    def _submit() -> None:
        nonlocal result
        parent = str(parent_var.get() or "").strip()
        name = str(name_var.get() or "").strip()
        if not parent:
            show_error("Parent folder must not be empty.")
            return
        if not name:
            show_error("Tree name must not be empty.")
            return
        result = {"artifact_root_parent": parent, "artifact_root_name": name}
        window.destroy()

    ctk.CTkButton(actions, text="Cancel", width=110, height=theme.BUTTON_HEIGHT, command=window.destroy).pack(side="right")
    ctk.CTkButton(actions, text="Create Artifact Tree", width=170, height=theme.BUTTON_HEIGHT, command=_submit).pack(side="right", padx=(0, 8))
    _focus_dialog(window, parent_entry)
    window.wait_window()
    return result


def _browse_parent(window, parent_var) -> None:
    selected = filedialog.askdirectory(
        parent=window,
        title="Select Artifact Tree Parent",
        initialdir=str(Path(parent_var.get()).expanduser()) if str(parent_var.get() or "").strip() else None,
    )
    if selected:
        parent_var.set(selected)


def _focus_dialog(window, entry) -> None:
    if hasattr(window, "lift"):
        window.lift()
    if hasattr(window, "focus_force"):
        window.focus_force()
    if hasattr(entry, "focus_set"):
        entry.focus_set()
