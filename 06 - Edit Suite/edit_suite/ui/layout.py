"""Widget layout for the Edit Suite shell."""
from __future__ import annotations

import customtkinter as ctk

from . import rendering, responsive, theme
from .scoped_scroll import ScopedScrollableFrame

WIDE_LAYOUT_WIDTH = 1180
COMPACT_MODULE_SCROLL_HEIGHT = 220
WIDE_MODULE_SCROLL_HEIGHT = 520


def build_shell(app, *, on_tab_change) -> dict:
    for index in range(2):
        app.grid_columnconfigure(index, weight=0)
        app.grid_rowconfigure(index, weight=0)

    sidebar = ctk.CTkFrame(app, corner_radius=0)
    sidebar.grid_rowconfigure(3, weight=1)
    sidebar.grid_columnconfigure(0, weight=1)

    sidebar_title = rendering.create_readonly_text(
        sidebar,
        text="Edit Suite",
        font=theme.font_header(),
        min_lines=1,
        max_lines=1,
        height=theme.INPUT_HEIGHT,
    )
    sidebar_title.grid(row=0, column=0, padx=theme.PADDING_LARGE, pady=(theme.PADDING_LARGE, theme.PADDING_SMALL), sticky="we")

    sidebar_subtitle = rendering.create_readonly_text(
        sidebar,
        text="Module-first shell for owner-provided config surfaces.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        min_lines=2,
        max_lines=3,
        height=50,
    )
    sidebar_subtitle.grid(row=1, column=0, padx=theme.PADDING_LARGE, pady=(0, theme.PADDING), sticky="we")

    source_label = rendering.create_readonly_text(
        sidebar,
        text="",
        font=theme.font_small(),
        min_lines=2,
        max_lines=4,
        height=52,
    )
    source_label.grid(row=2, column=0, padx=theme.PADDING_LARGE, pady=(0, theme.PADDING_SMALL), sticky="we")

    module_scroll = ScopedScrollableFrame(sidebar, corner_radius=0)
    module_scroll.grid(row=3, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="nsew")
    module_scroll.grid_columnconfigure(0, weight=1)

    refresh_button = ctk.CTkButton(sidebar, text="Refresh Registry", height=theme.BUTTON_HEIGHT, command=app.refresh_registry)
    refresh_button.grid(row=4, column=0, padx=theme.PADDING_LARGE, pady=(0, theme.PADDING_LARGE), sticky="we")

    detail = ctk.CTkFrame(app)
    detail.grid_columnconfigure(0, weight=1)
    detail.grid_rowconfigure(2, weight=1)

    title_label = rendering.create_readonly_text(
        detail,
        text="",
        font=theme.font_header(),
        min_lines=1,
        max_lines=2,
        height=theme.INPUT_HEIGHT,
    )
    title_label.grid(row=0, column=0, padx=theme.PADDING_LARGE, pady=(theme.PADDING_LARGE, 2), sticky="we")

    header_meta = ctk.CTkFrame(detail, fg_color=detail.cget("fg_color"))
    header_meta.grid(row=1, column=0, padx=theme.PADDING_LARGE, pady=(0, 2), sticky="we")
    header_meta.grid_columnconfigure(0, weight=1)

    subtitle_label = rendering.create_readonly_text(
        header_meta,
        text="",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        min_lines=1,
        max_lines=2,
        height=theme.INPUT_HEIGHT,
    )
    subtitle_label.grid(row=0, column=0, sticky="we")

    status_label = rendering.create_readonly_text(
        header_meta,
        text="",
        font=theme.font_small(),
        min_lines=1,
        max_lines=1,
        height=theme.INPUT_HEIGHT,
        justify="right",
    )
    status_label.grid(row=0, column=1, padx=(theme.PADDING_SMALL, 0), sticky="e")

    tabs = ctk.CTkTabview(detail, command=on_tab_change)
    tabs.grid(row=2, column=0, padx=theme.PADDING_LARGE, pady=(theme.PADDING_SMALL, theme.PADDING_LARGE), sticky="nsew")

    return {
        "sidebar": sidebar,
        "detail": detail,
        "header_meta": header_meta,
        "source_label": source_label,
        "module_scroll": module_scroll,
        "title_label": title_label,
        "subtitle_label": subtitle_label,
        "status_label": status_label,
        "tabs": tabs,
        "sections": {},
        "module_buttons": {},
    }


def build_section_tab(parent) -> dict:
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)
    scroll = ScopedScrollableFrame(parent)
    scroll.grid(row=0, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)
    return {"tab": parent, "scroll": scroll}


def apply_shell_layout(app, width: int) -> None:
    shell = getattr(app, "_shell", None)
    if not isinstance(shell, dict):
        return
    layout_mode = layout_mode_for_width(width)
    if not responsive.remember_layout_key(app, "edit_suite_shell", layout_mode):
        return
    if layout_mode == "compact":
        _apply_compact_layout(app, shell)
        return
    _apply_wide_layout(app, shell)


def layout_mode_for_width(width: int) -> str:
    return "compact" if width < WIDE_LAYOUT_WIDTH else "wide"


def _apply_compact_layout(app, shell: dict) -> None:
    for index in range(2):
        app.grid_columnconfigure(index, weight=0)
        app.grid_rowconfigure(index, weight=0)
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(1, weight=1)
    shell["sidebar"].grid(row=0, column=0, padx=theme.PADDING, pady=(theme.PADDING, theme.PADDING_SMALL), sticky="ew")
    shell["detail"].grid(row=1, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="nsew")
    shell["sidebar"].grid_rowconfigure(3, weight=0)
    shell["module_scroll"].configure(height=COMPACT_MODULE_SCROLL_HEIGHT)
    shell["subtitle_label"].grid(row=0, column=0, sticky="we")
    shell["status_label"].grid(row=1, column=0, padx=0, pady=(theme.PADDING_SMALL, 0), sticky="w")


def _apply_wide_layout(app, shell: dict) -> None:
    for index in range(2):
        app.grid_columnconfigure(index, weight=0)
        app.grid_rowconfigure(index, weight=0)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)
    shell["sidebar"].grid(row=0, column=0, padx=(theme.PADDING, theme.PADDING_SMALL), pady=theme.PADDING, sticky="nsew")
    shell["detail"].grid(row=0, column=1, padx=(0, theme.PADDING), pady=theme.PADDING, sticky="nsew")
    shell["sidebar"].grid_rowconfigure(3, weight=1)
    shell["module_scroll"].configure(height=WIDE_MODULE_SCROLL_HEIGHT)
    shell["subtitle_label"].grid(row=0, column=0, sticky="we")
    shell["status_label"].grid(row=0, column=1, padx=(theme.PADDING_SMALL, 0), pady=0, sticky="e")
