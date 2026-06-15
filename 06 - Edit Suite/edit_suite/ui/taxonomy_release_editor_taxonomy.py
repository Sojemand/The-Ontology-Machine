"""Taxonomy-section controller for the Semantic Release editor."""

from __future__ import annotations

import copy

import customtkinter as ctk

from . import theme
from .taxonomy_release_editor_widgets import _replace_entry
from .taxonomy_release_model import _csv, _item_key, _key_name, _taxonomy_items


def _refresh_taxonomy_list(frame) -> None:
    for child in frame._taxonomy_list.winfo_children():
        child.destroy()
    section = frame._taxonomy_section.get()
    items = _taxonomy_items(frame, section)
    if frame._selected_taxonomy_index >= len(items):
        frame._selected_taxonomy_index = max(0, len(items) - 1)
    for row, item in enumerate(items):
        key = _item_key(item)
        label = str(item.get("label") or item.get("description") or key or "(new)")
        border = 1 if row == frame._selected_taxonomy_index else 0
        ctk.CTkButton(
            frame._taxonomy_list,
            text=f"{label}\n{key}",
            anchor="w",
            border_width=border,
            command=lambda index=row, target=frame: _select_taxonomy_item(target, index),
        ).grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=3, sticky="we")


def _show_taxonomy_item(frame) -> None:
    items = _taxonomy_items(frame, frame._taxonomy_section.get())
    item = items[frame._selected_taxonomy_index] if items and 0 <= frame._selected_taxonomy_index < len(items) else {}
    values = {
        "key": _item_key(item),
        "label": item.get("label", ""),
        "description": item.get("description", ""),
        "aliases": ", ".join(str(value) for value in item.get("aliases", []) or []),
        "status": item.get("status", ""),
        "parent_id": item.get("parent_id", ""),
    }
    for name, widget in frame._taxonomy_widgets.items():
        _replace_entry(widget, values.get(name, ""))


def _select_taxonomy_section(frame) -> None:
    _sync_current_taxonomy_item(frame)
    frame._selected_taxonomy_index = 0
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)


def _select_taxonomy_item(frame, index: int) -> None:
    if index != frame._selected_taxonomy_index:
        _sync_current_taxonomy_item(frame)
    frame._selected_taxonomy_index = index
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)


def _sync_current_taxonomy_item(frame) -> None:
    items = _taxonomy_items(frame, frame._taxonomy_section.get())
    if not items or not (0 <= frame._selected_taxonomy_index < len(items)):
        return
    item = items[frame._selected_taxonomy_index]
    key_name = _key_name(frame._taxonomy_section.get())
    key_value = frame._taxonomy_widgets["key"].get().strip()
    if key_value:
        item[key_name] = key_value
    for field_name in ("label", "description", "status", "parent_id"):
        value = frame._taxonomy_widgets[field_name].get().strip()
        if value:
            item[field_name] = value
        else:
            item.pop(field_name, None)
    aliases = _csv(frame._taxonomy_widgets["aliases"].get())
    if aliases:
        item["aliases"] = aliases
    else:
        item.pop("aliases", None)

def _new_taxonomy_item(frame) -> None:
    _sync_current_taxonomy_item(frame)
    section = frame._taxonomy_section.get()
    item = {_key_name(section): "", "label": "", "description": ""}
    _taxonomy_items(frame, section).append(item)
    frame._selected_taxonomy_index = len(_taxonomy_items(frame, section)) - 1
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)


def _duplicate_taxonomy_item(frame) -> None:
    _sync_current_taxonomy_item(frame)
    items = _taxonomy_items(frame, frame._taxonomy_section.get())
    if not items:
        return
    payload = copy.deepcopy(items[frame._selected_taxonomy_index])
    payload[_key_name(frame._taxonomy_section.get())] = ""
    payload["label"] = ""
    items.append(payload)
    frame._selected_taxonomy_index = len(items) - 1
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)


def _delete_taxonomy_item(frame) -> None:
    items = _taxonomy_items(frame, frame._taxonomy_section.get())
    if 0 <= frame._selected_taxonomy_index < len(items):
        del items[frame._selected_taxonomy_index]
    frame._selected_taxonomy_index = min(frame._selected_taxonomy_index, max(0, len(items) - 1))
    _refresh_taxonomy_list(frame)
    _show_taxonomy_item(frame)
