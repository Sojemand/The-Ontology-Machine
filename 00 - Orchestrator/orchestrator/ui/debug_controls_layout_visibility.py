"""Visibility and layout helpers for the debug console."""

from __future__ import annotations

from . import responsive
from .debug_controls_layout_helpers import apply_console_grid


def apply_layout(app, order: tuple[str, ...]) -> None:
    cards = [app._debug_console_cards[key] for key in order if getattr(app._debug_console_cards[key], "visible", True)]
    wrap = responsive.wrap_for_columns(responsive.current_width(app), 1, minimum=280, maximum=720, padding=220)
    layout_key = (tuple(key for key in order if getattr(app._debug_console_cards[key], "visible", True)), wrap)
    if not responsive.remember_layout_key(app, "debug_console", layout_key):
        return
    for key in order:
        card = app._debug_console_cards[key]
        if not getattr(card, "visible", True) and hasattr(card, "grid_forget"):
            card.grid_forget()
    apply_console_grid(app._debug_console_grid, cards, columns=1)
    responsive.set_wrap(app._debug_target_hint_label, wrap)


def row_visible(app, key: str) -> bool:
    return bool(getattr(app._debug_control_rows.get(key), "visible", False))


def target_hint(uses_module_input: bool, mode: str) -> str:
    if uses_module_input and mode == "single":
        return "Single uses the directly selected module file under Input Path."
    if uses_module_input:
        return "Input Path provides the batch or scan input directly to the target module."
    if mode == "single":
        return "Source Path selects the concrete original file for this debug session, not raw_extracts/*.raw.json."
    return "Input Path provides the batch or scan input for this debug session."
