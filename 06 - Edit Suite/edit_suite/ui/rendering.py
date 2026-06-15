"""Rendering helpers for the Edit Suite UI."""
from __future__ import annotations

import customtkinter as ctk

from . import theme
from .section_intro import render_section_intro, section_body_limits
from .summary_cards import render_summary_card
from .surface_cards import render_surface_card
from .text_widgets import create_readonly_text, render_source_label, set_readonly_text
from .view_model import DetailView, ModuleListItem

_section_body_limits = section_body_limits


def render_module_list(
    container,
    rows: dict[str, ctk.CTkFrame],
    items: tuple[ModuleListItem, ...],
    *,
    selected_key: str,
    select_module,
) -> dict[str, ctk.CTkFrame]:
    for row in rows.values():
        row.destroy()
    new_rows: dict[str, ctk.CTkFrame] = {}
    for index, item in enumerate(items):
        row = ctk.CTkFrame(container, border_width=1 if item.key == selected_key else 0, border_color=theme.COLOR_ACCENT)
        row.grid(row=index, column=0, padx=4, pady=4, sticky="we")
        row.grid_columnconfigure(0, weight=1)
        summary = create_readonly_text(row, text=_module_summary(item), font=theme.font_normal(), min_lines=3, max_lines=4, height=74)
        summary.grid(row=0, column=0, padx=(theme.PADDING_SMALL, 0), pady=theme.PADDING_SMALL, sticky="nsew")
        ctk.CTkButton(row, text="Open", width=76, height=theme.BUTTON_HEIGHT, command=lambda key=item.key: select_module(key)).grid(
            row=0,
            column=1,
            padx=theme.PADDING_SMALL,
            pady=theme.PADDING_SMALL,
            sticky="e",
        )
        new_rows[item.key] = row
    return new_rows


def render_shell_chrome(
    shell: dict,
    *,
    source: str,
    stale: bool,
    message: str,
    items: tuple[ModuleListItem, ...],
    selected_key: str,
    select_module,
) -> None:
    render_source_label(shell["source_label"], source=source, stale=stale, message=message)
    shell["module_buttons"] = render_module_list(
        shell["module_scroll"],
        shell["module_buttons"],
        items,
        selected_key=selected_key,
        select_module=select_module,
    )


def render_detail_header(shell: dict, detail: DetailView | None) -> None:
    if detail is None:
        set_readonly_text(shell["title_label"], "", min_lines=1, max_lines=2)
        set_readonly_text(shell["subtitle_label"], "", min_lines=1, max_lines=2)
        set_readonly_text(shell["status_label"], "", min_lines=1, max_lines=1, justify="right")
        return
    set_readonly_text(shell["title_label"], detail.title, min_lines=1, max_lines=2)
    set_readonly_text(shell["subtitle_label"], detail.subtitle, min_lines=1, max_lines=2)
    set_readonly_text(shell["status_label"], detail.status, min_lines=1, max_lines=1, justify="right")


def render_section(container, section, *, app, width: int) -> dict[str, dict]:
    action_widgets: dict[str, dict] = {}
    for child in container.winfo_children():
        child.destroy()
    row = render_section_intro(container, section.name, section.headline, section.body, row=0)
    for card in section.summary_cards:
        row = render_summary_card(container, card, row=row)
    for surface in section.surfaces:
        rendered = render_surface_card(container, surface, app=app, row=row, width=width)
        _register_action_widget(action_widgets, surface, rendered)
        row += 1
    return action_widgets


def render_detail(shell: dict, detail: DetailView, *, selected_section: str, app) -> dict[str, dict]:
    render_detail_header(shell, detail)
    action_widgets: dict[str, dict] = {}
    for section in detail.sections:
        container = shell["sections"][section.name]["scroll"]
        section_widgets = render_section(container, section, app=app, width=theme.WINDOW_MIN_WIDTH)
        action_widgets.update(section_widgets)
    shell["tabs"].set(selected_section)
    return action_widgets


def _module_summary(item: ModuleListItem) -> str:
    lines = [item.title]
    if item.subtitle:
        lines.append(item.subtitle)
    lines.append(f"Status: {item.badge}")
    return "\n".join(lines)


def _register_action_widget(action_widgets: dict[str, dict], surface, rendered: dict) -> None:
    if surface.editable and surface.editor_kind not in {"readonly", "preview"}:
        action_widgets.setdefault(surface.surface_id, rendered)
        return
    buttons = surface.descriptor.get("action_buttons")
    if surface.editor_kind == "operation" or (isinstance(buttons, list) and buttons):
        action_widgets.setdefault(surface.surface_id, rendered)
