"""Draft readers for Edit Suite surface widgets."""

from __future__ import annotations

import json

from .form_fields import read_form_value
from .nested_policy_editor import read_value as read_nested_policy_value
from . import prompt_bundle_editor, taxonomy_release_editor


def read_widget_value(action_widgets: dict[str, dict], surface_id: str) -> dict:
    widget_info = action_widgets.get(surface_id)
    if widget_info is None:
        raise ValueError(f"No editable surface loaded for {surface_id}.")
    widget = widget_info["editor"]
    surface = widget_info["surface"]
    if surface.editor_kind == "form":
        return read_form_value(widget)
    if surface.editor_kind == "nested_policy":
        return read_nested_policy_value(widget)
    if surface.editor_kind == "prompt_bundle":
        return prompt_bundle_editor.read_value(widget)
    if surface.editor_kind == "taxonomy_release_draft":
        return taxonomy_release_editor.read_value(widget)
    return _parse_json_payload(widget.get("1.0", "end").strip())


def fallback_draft_value(action_widgets: dict[str, dict], surface_id: str) -> dict:
    widget_info = action_widgets.get(surface_id) or {}
    surface = widget_info.get("surface")
    return dict(getattr(surface, "draft", {}) or {})


def _parse_json_payload(raw_text: str) -> dict:
    payload = json.loads(raw_text or "{}")
    if not isinstance(payload, dict):
        raise ValueError("Editor must contain a JSON object.")
    return payload
