"""Run-console layout and visibility for the orchestrator debug-host tab."""

from __future__ import annotations

import customtkinter as ctk

from . import debug_repository, debug_view_support, responsive, theme
from . import debug_controls_layout_helpers as layout_helpers
from .debug_controls_layout_helpers import (
    card as build_card,
    check_toggle_row,
    field_row,
    hash_row,
    option_menu_row,
    persist_page_images_row,
    set_card_visible,
)
from .debug_controls_layout_visibility import apply_layout, row_visible, target_hint

_ORDER = ("target", "advanced", "run_control")
_ADVANCED_ROWS = ("format", "doc_type", "max_size_mb", "batch_size", "worker_count", "raw_path", "raw_root", "hash_tools", "persist_page_images", "check_toggles")


def build_debug_console(app, parent) -> None:
    layout_helpers.ctk = ctk
    module_key = debug_repository.default_module_key(app)
    mode = debug_repository.default_mode_for_module(app, module_key)
    app._debug_control_rows = {}
    app._debug_artifact_buttons = []
    app._debug_module_var = ctk.StringVar(value=module_key)
    app._debug_mode_var = ctk.StringVar(value=mode)
    app._debug_console_frame = ctk.CTkFrame(parent, fg_color="transparent")
    app._debug_console_frame.pack(fill="x", padx=theme.PADDING, pady=(0, theme.PADDING_SMALL))
    app._debug_console_grid = ctk.CTkFrame(app._debug_console_frame, fg_color="transparent")
    app._debug_console_grid.pack(fill="x")
    app._debug_console_cards = {
        "target": _build_target_card(app),
        "advanced": _build_advanced_card(app),
        "run_control": _build_run_control_card(app),
    }
    set_card_visible(app._debug_console_cards["target"], True)
    set_card_visible(app._debug_console_cards["advanced"], False)
    set_card_visible(app._debug_console_cards["run_control"], True)
    responsive.register_resize_callback(app, "debug_console", lambda width: _apply_layout(app, width))


def apply_console_state(app, descriptor, state: dict[str, object]) -> None:
    uses_module_input = debug_repository.uses_module_selected_input(descriptor)
    mode = str(state.get("mode", "")).strip().lower()
    uses_debug_input_path = uses_module_input or mode != "single"
    controls = set(getattr(descriptor, "controls", ()))
    debug_view_support.set_row_visible(app._debug_control_rows.get("input_path"), uses_debug_input_path)
    debug_view_support.set_row_visible(app._debug_control_rows.get("source_path"), not uses_module_input and mode == "single")
    for key in ("format", "doc_type", "max_size_mb", "batch_size"):
        debug_view_support.set_row_visible(app._debug_control_rows.get(key), "filters" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("worker_count"), "worker_count" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("hash_tools"), "hash_tools" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("raw_path"), "raw_evidence" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("raw_root"), "raw_evidence" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("persist_page_images"), "persist_page_images" in controls)
    debug_view_support.set_row_visible(app._debug_control_rows.get("check_toggles"), "check_toggles" in controls)
    if hasattr(app, "_debug_source_entry"):
        app._debug_source_entry.configure(state="normal" if not uses_module_input and mode == "single" else "disabled")
    if hasattr(app, "_debug_input_entry"):
        app._debug_input_entry.configure(state="normal" if uses_debug_input_path else "disabled")
    app._debug_target_hint_label.configure(text=target_hint(uses_module_input, mode))
    set_card_visible(app._debug_console_cards["target"], True)
    set_card_visible(app._debug_console_cards["run_control"], True)
    set_card_visible(app._debug_console_cards["advanced"], any(row_visible(app, key) for key in _ADVANCED_ROWS))
    apply_layout(app, _ORDER)


def _build_target_card(app):
    card = build_card(app._debug_console_grid, "Target")
    module_values = debug_repository.descriptor_keys(app) or [app._debug_module_var.get()]
    mode_values = list(debug_repository.supported_modes_for_module(app, app._debug_module_var.get())) or [app._debug_mode_var.get()]
    option_menu_row(app, card, "Module", "_debug_module_menu", variable=app._debug_module_var, values=module_values)
    option_menu_row(app, card, "Mode", "_debug_mode_menu", variable=app._debug_mode_var, values=mode_values)
    app._debug_control_rows["input_path"] = field_row(app, card, "Input Path", "_debug_input_entry", button_text="Browse", button_command=app._browse_debug_input)
    app._debug_control_rows["source_path"] = field_row(app, card, "Source Path", "_debug_source_entry", button_text="Browse", button_command=app._browse_debug_source)
    app._debug_target_hint_label = ctk.CTkLabel(card, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left")
    app._debug_target_hint_label.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    return card


def _build_advanced_card(app):
    card = build_card(app._debug_console_grid, "Advanced")
    app._debug_control_rows["format"] = field_row(app, card, "Format", "_debug_format_entry")
    app._debug_control_rows["doc_type"] = field_row(app, card, "Doc Type", "_debug_doc_type_entry")
    app._debug_control_rows["max_size_mb"] = field_row(app, card, "Max Size MB", "_debug_size_entry")
    app._debug_control_rows["batch_size"] = field_row(app, card, "Batch Size", "_debug_batch_entry")
    app._debug_control_rows["worker_count"] = field_row(app, card, "Worker", "_debug_worker_entry")
    app._debug_control_rows["raw_path"] = field_row(app, card, "Raw JSON", "_debug_raw_entry")
    app._debug_control_rows["raw_root"] = field_row(app, card, "Raw Folder", "_debug_raw_root_entry")
    app._debug_hash_var = ctk.BooleanVar(value=True)
    app._debug_control_rows["hash_tools"] = hash_row(app, card)
    app._debug_persist_page_images_var = ctk.BooleanVar(value=False)
    app._debug_control_rows["persist_page_images"] = persist_page_images_row(app, card)
    app._debug_control_rows["check_toggles"] = check_toggle_row(app, card)
    return card


def _build_run_control_card(app):
    card = build_card(app._debug_console_grid, "Run Control")
    grid = ctk.CTkFrame(card, fg_color="transparent")
    grid.pack(fill="x", padx=theme.PADDING_SMALL, pady=(theme.PADDING_SMALL, 10))
    for column in range(2):
        grid.grid_columnconfigure(column, weight=1)
    buttons = (
        ("_debug_start_btn", "Start", app._start_debug_session, theme.COLOR_ACCENT),
        ("_debug_refresh_btn", "Refresh", app._refresh_debug_session, None),
        ("_debug_cancel_btn", "Cancel", app._cancel_debug_session, theme.COLOR_WARNING),
        ("_debug_open_btn", "Open Artifacts", app._open_debug_artifacts, None),
        ("_debug_help_btn", "Help", app._show_debug_help, None),
    )
    for index, (attr_name, text, command, color) in enumerate(buttons):
        kwargs = {"text": text, "command": command}
        if color:
            kwargs["fg_color"] = color
            kwargs["hover_color"] = color
        button = ctk.CTkButton(grid, **kwargs)
        grid_kwargs = {"row": index // 2, "column": index % 2, "sticky": "ew", "padx": 4, "pady": 4}
        if attr_name == "_debug_help_btn":
            grid_kwargs.update({"row": 2, "column": 0, "columnspan": 2})
        button.grid(**grid_kwargs)
        setattr(app, attr_name, button)
    return card


def _apply_layout(app, width: int) -> None:
    del width
    apply_layout(app, _ORDER)
