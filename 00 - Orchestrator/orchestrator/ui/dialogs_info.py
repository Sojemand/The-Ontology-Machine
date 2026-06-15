"""Information window dialogs for the Orchestrator UI."""

from __future__ import annotations

import customtkinter as ctk

from . import theme


def show_info_window(app, *, title: str, body: str) -> None:
    existing = getattr(app, "_info_window", None)
    if existing is not None:
        try:
            if bool(existing.winfo_exists()):
                existing.destroy()
        except Exception:
            pass
    window = ctk.CTkToplevel(app)
    app._info_window = window
    window.title(f"Orchestrator | {title}")
    window.geometry("760x620")
    window.minsize(620, 420)
    if hasattr(window, "transient"):
        window.transient(app)
    root = ctk.CTkFrame(window)
    root.pack(fill="both", expand=True, padx=theme.PADDING, pady=theme.PADDING)
    ctk.CTkLabel(root, text=title, font=theme.font_header(), text_color=theme.COLOR_TEXT, anchor="w", justify="left").pack(fill="x")
    ctk.CTkLabel(root, text=_info_window_subtitle(title), font=theme.font_small(), text_color=theme.COLOR_MUTED, anchor="w", justify="left").pack(fill="x", pady=(2, theme.PADDING_SMALL))
    text = ctk.CTkTextbox(root, font=theme.font_normal(), wrap="word")
    text.pack(fill="both", expand=True, pady=(0, theme.PADDING_SMALL))
    text.insert("1.0", body.strip())
    text.configure(state="disabled")
    ctk.CTkButton(root, text="Close", width=110, height=theme.BUTTON_HEIGHT, command=window.destroy).pack(anchor="e")
    if hasattr(window, "lift"):
        window.lift()
    if hasattr(window, "focus_force"):
        window.focus_force()


def _info_window_subtitle(title: str) -> str:
    normalized = str(title).strip().lower()
    if "status" in normalized:
        return "Run-control guide plus short Edit Suite orientation"
    return "Module-specific debug guidance"
