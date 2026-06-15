"""Surface-card rendering for the Edit Suite detail view."""
from __future__ import annotations

import json

import customtkinter as ctk

from . import action_forms
from . import form_fields
from . import nested_policy_editor
from . import operation_runner
from . import preview_result_view
from . import prompt_bundle_editor
from . import review_result_view
from . import support_monitor_editor
from . import taxonomy_release_editor
from . import theme
from .text_widgets import create_json_textbox, create_readonly_text

_EDITABLE_EDITOR_KINDS = {
    "form",
    "json",
    "nested_policy",
    "prompt_bundle",
    "taxonomy_release_draft",
}


def render_surface_card(container, surface, *, app, row: int, width: int = theme.WINDOW_MIN_WIDTH) -> dict:
    card = ctk.CTkFrame(container)
    card.grid(row=row, column=0, padx=theme.PADDING_SMALL, pady=theme.PADDING_SMALL, sticky="we")
    card.grid_columnconfigure(0, weight=1)
    meta = _surface_meta(surface)
    status_text = surface.message or ("Draft changed" if surface.dirty else "Current state")
    status_color = theme.COLOR_ERROR if status_text.startswith("Error") else theme.COLOR_SUCCESS
    create_readonly_text(card, text=surface.label, font=theme.font_header(), min_lines=1, max_lines=2, height=theme.INPUT_HEIGHT).grid(
        row=0,
        column=0,
        padx=theme.PADDING,
        pady=(theme.PADDING, 2),
        sticky="we",
    )
    meta_row = ctk.CTkFrame(card, fg_color=card.cget("fg_color"))
    meta_row.grid(row=1, column=0, padx=theme.PADDING, pady=(0, 2), sticky="we")
    meta_row.grid_columnconfigure(0, weight=1)
    create_readonly_text(meta_row, text=meta, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=2).grid(row=0, column=0, sticky="we")
    create_readonly_text(
        meta_row,
        text=status_text,
        font=theme.font_small(),
        text_color=status_color,
        min_lines=1,
        max_lines=2,
        justify="right",
    ).grid(row=0, column=1, padx=(theme.PADDING_SMALL, 0), sticky="e")
    widget = _editor_widget(card, surface, app=app, width=width)
    widget.grid(row=2, column=0, padx=theme.PADDING, pady=(theme.PADDING_SMALL, theme.PADDING_SMALL), sticky="nsew")
    action_row = _render_action_buttons(card, surface, app=app, row=3)
    _render_operation_result(card, app=app, surface_id=surface.surface_id, row=action_row + 1)
    return {"surface": surface, "editor": widget}


def _editor_widget(parent, surface, *, app, width: int):
    if surface.editor_kind == "operation":
        return action_forms.render_action_editor(parent, surface, app=app)
    if surface.editor_kind == "review_result":
        return review_result_view.render(parent, surface)
    if surface.editor_kind == "preview_result":
        return preview_result_view.render(parent, surface)
    if surface.editor_kind == "prompt_bundle":
        return prompt_bundle_editor.render(parent, surface)
    if surface.editor_kind == "taxonomy_release_draft":
        return taxonomy_release_editor.render(parent, surface, app=app)
    if surface.editor_kind == "support_monitor":
        return support_monitor_editor.render(parent, surface, app=app)
    if surface.editor_kind == "nested_policy":
        return nested_policy_editor.render(parent, surface, width=width)
    if surface.editor_kind == "form":
        return form_fields.render_form_editor(parent, surface, width=width)
    textbox = create_json_textbox(parent)
    value = surface.draft if surface.editor_kind == "json" else surface.value
    textbox.insert("1.0", json.dumps(value, indent=2, ensure_ascii=False))
    if surface.editor_kind != "json":
        textbox.configure(state="disabled")
    return textbox


def _render_action_buttons(card, surface, *, app, row: int) -> int:
    action_links = _action_links(surface)
    show_edit_actions = surface.editable and surface.editor_kind in _EDITABLE_EDITOR_KINDS
    show_inline_actions = surface.editor_kind == "operation" or bool(surface.descriptor.get("render_actions_inline", True))
    button_state = getattr(app, "action_button_state", lambda _sid: "disabled" if getattr(app, "entry_is_loading", lambda: False)() else "normal")(surface.surface_id)
    if not show_edit_actions and (not show_inline_actions or not action_links):
        return row - 1
    actions = ctk.CTkFrame(card, fg_color=card.cget("fg_color"))
    actions.grid(row=row, column=0, padx=theme.PADDING, pady=(0, theme.PADDING), sticky="we")
    next_column = 0
    if show_edit_actions:
        validate_label = str(surface.descriptor.get("validate_label") or "Validate")
        save_label = str(surface.descriptor.get("save_label") or "Save")
        ctk.CTkButton(actions, text=validate_label, width=100, state=button_state, command=lambda sid=surface.surface_id: app.validate_surface(sid)).grid(
            row=0, column=0, padx=(0, theme.PADDING_SMALL), sticky="w"
        )
        ctk.CTkButton(actions, text=save_label, width=100, state=button_state, command=lambda sid=surface.surface_id: app.save_surface(sid)).grid(
            row=0, column=1, padx=(0, theme.PADDING_SMALL), sticky="w"
        )
        next_column = 2
    if show_inline_actions:
        for index, action_link in enumerate(action_links, start=next_column):
            label = str(action_link.get("label") or action_link.get("action") or "Action")
            ctk.CTkButton(
                actions,
                text=label,
                width=128,
                state=button_state,
                command=lambda sid=surface.surface_id, link=action_link: app.run_surface_action(sid, link),
            ).grid(row=0, column=index, padx=(0, theme.PADDING_SMALL), sticky="w")
    return row


def _render_operation_result(card, *, app, surface_id: str, row: int) -> None:
    result = app.operation_result_text(surface_id)
    current_row = row
    if not result:
        choices = operation_runner.merge_interaction_choices(app, surface_id)
        if not choices:
            return
    if result:
        create_readonly_text(
            card,
            text=result,
            font=theme.font_small(),
            text_color=theme.COLOR_MUTED,
            min_lines=2,
            max_lines=10,
        ).grid(row=current_row, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="we")
        current_row += 1
    choices = operation_runner.merge_interaction_choices(app, surface_id)
    if not choices:
        return
    buttons = ctk.CTkFrame(card, fg_color=card.cget("fg_color"))
    buttons.grid(row=current_row, column=0, padx=theme.PADDING, pady=(0, theme.PADDING_SMALL), sticky="w")
    button_state = getattr(app, "action_button_state", lambda _sid: "normal")(surface_id)
    for index, choice in enumerate(choices):
        ctk.CTkButton(
            buttons,
            text=str(choice.get("label") or choice.get("choice_id") or "Continue"),
            width=180,
            state=button_state,
            command=lambda sid=surface_id, cid=str(choice.get("choice_id") or ""): app.resolve_merge_interaction(sid, cid),
        ).grid(row=0, column=index, padx=(0, theme.PADDING_SMALL), sticky="w")


def _action_links(surface) -> tuple[dict, ...]:
    buttons = surface.descriptor.get("action_buttons")
    if isinstance(buttons, list) and buttons:
        return tuple(link for link in buttons if isinstance(link, dict))
    return tuple(link for link in surface.operation_links if isinstance(link, dict))


def _grouped_fields(surface) -> list[tuple[str, list[str]]]:
    return form_fields.grouped_fields(surface)


def _surface_meta(surface) -> str:
    source_path = str(surface.descriptor.get("source_path", "")).strip()
    return f"{surface.kind} | {source_path}" if source_path else surface.kind


def uses_compact_form_layout(width: int) -> bool:
    return form_fields.uses_compact_form_layout(width)


def _prompt_bundle_fields(payload: dict) -> list[tuple[str, str]]:
    return prompt_bundle_editor.fields(payload)


def _prompt_bundle_actual_text(values: dict[str, str]) -> str:
    return prompt_bundle_editor.actual_text(values)
