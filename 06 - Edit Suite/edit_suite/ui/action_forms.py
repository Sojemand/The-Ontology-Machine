"""Generic owner-action input widgets for synthetic operation cards."""
from __future__ import annotations

from tkinter import filedialog as fd

import customtkinter as ctk

from .action_workflow_text import details_text
from . import action_path_dialogs, theme
from .text_widgets import create_readonly_text


def render_action_editor(parent, surface, *, app):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    action_link = next(iter(surface.operation_links), {})
    summary = str(surface.descriptor.get("operation_summary") or surface.value.get("summary") or "").strip()
    row = 0
    if summary:
        create_readonly_text(frame, text=summary, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=2, max_lines=5).grid(
            row=row, column=0, sticky="we"
        )
        row += 1
    details = details_text(action_link)
    if details:
        create_readonly_text(frame, text=details, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=3, max_lines=8).grid(
            row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we"
        )
        row += 1
    widgets = {}
    for spec in _input_specs(action_link):
        row = _render_field(frame, row, spec, widgets, app=app)
    frame._action_inputs = widgets
    return frame


def read_action_payload(app, surface_id: str, action_link: dict) -> dict:
    widget_info = app._action_widgets.get(surface_id) or {}
    editor = widget_info.get("editor")
    specs = getattr(editor, "_action_inputs", None)
    if not isinstance(specs, dict):
        return {}
    module_context = _module_context(app)
    payload = {}
    for name, item in specs.items():
        spec = item["spec"]
        value = _read_value(item)
        if (value == "" or value is None) and not bool(spec.get("required")):
            module_context.pop(str(spec.get("persist_key") or name), None)
            continue
        if value == "" or value is None:
            raise ValueError(f"{name} is missing or invalid.")
        payload[name] = value
        module_context[str(spec.get("persist_key") or name)] = value
    return payload


def _render_field(parent, row: int, spec: dict, widgets: dict[str, dict], *, app) -> int:
    label = create_readonly_text(parent, text=str(spec.get("label") or spec["name"]), font=theme.font_small(), text_color=theme.COLOR_MUTED)
    label.grid(row=row, column=0, pady=(theme.PADDING_SMALL, 2), sticky="w")
    row += 1
    field_type = str(spec.get("field_type") or "text")
    initial = _initial_value(app, spec)
    if field_type == "checkbox":
        variable = ctk.BooleanVar(value=bool(initial))
        widget = ctk.CTkCheckBox(parent, text=str(spec.get("checkbox_label") or "Enabled"), variable=variable, onvalue=True, offvalue=False)
        widget.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="w")
        widgets[spec["name"]] = {"spec": spec, "kind": field_type, "variable": variable, "widget": widget}
        return row + 1
    if field_type == "select":
        values, labels = _select_options(spec)
        variable = ctk.StringVar(value=_resolve_select_value(initial, values))
        widget = ctk.CTkOptionMenu(parent, values=list(labels), command=lambda choice, var=variable, mapping=labels: var.set(mapping[choice]))
        if labels:
            widget.set(next((label for label, value in labels.items() if value == variable.get()), next(iter(labels))))
        widget.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
        widgets[spec["name"]] = {"spec": spec, "kind": field_type, "variable": variable, "widget": widget}
        return row + 1
    if field_type in {"open_file", "open_folder", "save_file"}:
        field = ctk.CTkFrame(parent, fg_color=parent.cget("fg_color"))
        field.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
        field.grid_columnconfigure(0, weight=1)
        widget = ctk.CTkEntry(field, height=theme.INPUT_HEIGHT)
        widget.insert(0, "" if initial is None else str(initial))
        widget.grid(row=0, column=0, padx=(0, theme.PADDING_SMALL), sticky="we")
        ctk.CTkButton(
            field,
            text="Browse",
            width=90,
            command=lambda entry=widget, kind=field_type, field_spec=spec, field_widgets=widgets: _choose_path(
                app,
                entry,
                kind,
                spec=field_spec,
                widgets=field_widgets,
            ),
        ).grid(row=0, column=1, sticky="e")
        widgets[spec["name"]] = {"spec": spec, "kind": field_type, "widget": widget}
        return row + 1
    if field_type == "multiline_text":
        widget = ctk.CTkTextbox(parent, height=int(spec.get("height") or 104), wrap="word", font=theme.font_normal())
        if initial not in (None, ""):
            widget.insert("1.0", str(initial))
        widget.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
        widgets[spec["name"]] = {"spec": spec, "kind": field_type, "widget": widget}
        return row + 1
    widget = ctk.CTkEntry(parent, height=theme.INPUT_HEIGHT)
    widget.insert(0, "" if initial is None else str(initial))
    widget.grid(row=row, column=0, pady=(0, theme.PADDING_SMALL), sticky="we")
    widgets[spec["name"]] = {"spec": spec, "kind": field_type, "widget": widget}
    return row + 1


def _read_value(item: dict):
    kind = item["kind"]
    if kind == "checkbox":
        return bool(item["variable"].get())
    if kind == "select":
        return str(item["variable"].get()).strip()
    if kind == "multiline_text":
        return str(item["widget"].get("1.0", "end")).strip()
    raw = str(item["widget"].get()).strip()
    if raw == "":
        return ""
    if kind == "number":
        return int(raw) if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()) else float(raw)
    return raw


def _input_specs(action_link: dict) -> tuple[dict, ...]:
    raw = action_link.get("inputs")
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, dict) and str(item.get("name") or "").strip())


def _initial_value(app, spec: dict):
    value = _module_context(app).get(str(spec.get("persist_key") or spec["name"]))
    if value is not None and value != "":
        return value
    return spec.get("default")


def _module_context(app) -> dict:
    contexts = app._ui_state.setdefault("operation_contexts", {})
    current = contexts.get(app._selected_module)
    if not isinstance(current, dict):
        current = {}
        contexts[app._selected_module] = current
    return current


def _select_options(spec: dict) -> tuple[list[str], dict[str, str]]:
    values = []
    labels = {}
    for item in spec.get("options") or []:
        if isinstance(item, dict):
            value = str(item.get("value") or "")
            label = str(item.get("label") or value)
        else:
            value = str(item)
            label = value
        if value:
            values.append(value)
            labels[label] = value
    return values, labels


def _resolve_select_value(current, values: list[str]) -> str:
    text = str(current or "").strip()
    return text if text in values else (values[0] if values else "")


def _choose_path(app, entry, field_type: str, *, spec: dict | None = None, widgets: dict | None = None) -> None:
    action_path_dialogs.choose_path(app, entry, field_type, spec=spec, widgets=widgets, filedialog=fd)
