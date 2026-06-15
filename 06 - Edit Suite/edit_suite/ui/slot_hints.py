"""Inline slot-hint rendering for structured owner-provided editors."""
from __future__ import annotations

from . import theme
from .text_widgets import create_readonly_text


def resolve_descriptor(slot_descriptors: dict, field_path: str, *, prefix: str = "") -> dict:
    if not isinstance(slot_descriptors, dict):
        return {}
    candidates = [field_path]
    if prefix:
        candidates.append(f"{prefix}.{field_path}")
    if field_path.startswith("core."):
        candidates.extend(["core", f"{prefix}.core" if prefix else ""])
    for candidate in candidates:
        if candidate and isinstance(slot_descriptors.get(candidate), dict):
            return dict(slot_descriptors[candidate])
    return {}


def slot_hint_text(descriptor: dict) -> str:
    if not isinstance(descriptor, dict) or not descriptor:
        return ""
    lines = []
    role = str(descriptor.get("role") or "").strip()
    relevance = str(descriptor.get("compile_relevance") or "").strip()
    if role or relevance:
        lines.append(" | ".join(part for part in (role, relevance) if part))
    allowed = _as_text_list(descriptor.get("allowed_values"))
    references = _as_text_list(descriptor.get("reference_types"))
    if allowed:
        lines.append(f"Allowed: {', '.join(allowed[:3])}")
    if references:
        lines.append(f"Refs: {', '.join(references[:3])}")
    validators = _as_text_list(descriptor.get("validators"))
    downstream = _as_text_list(descriptor.get("downstream_consumers") or descriptor.get("used_by_modules"))
    if validators:
        lines.append(f"Validators: {', '.join(validators[:2])}")
    if downstream:
        lines.append(f"Downstream: {', '.join(downstream[:3])}")
    for key, label in (("compile_effect", "Compile"), ("prompt_effect", "Prompt"), ("corpus_effect", "Corpus")):
        value = str(descriptor.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines[:5])


def render_slot_hint(parent, descriptor: dict, *, row: int, column: int = 0) -> int:
    text = slot_hint_text(descriptor)
    if not text:
        return row
    create_readonly_text(parent, text=text, font=theme.font_small(), text_color=theme.COLOR_MUTED, min_lines=1, max_lines=5).grid(
        row=row,
        column=column,
        padx=theme.PADDING_SMALL,
        pady=(0, theme.PADDING_SMALL),
        sticky="we",
    )
    return row + 1


def _as_text_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]

