"""Readable preview/result rendering for source workflow cards."""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from . import theme
from .text_widgets import create_readonly_text


def render(parent, surface):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    for row, (label, body) in enumerate(sections_from_value(surface.value or {})):
        create_readonly_text(frame, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(
            row=row * 2, column=0, pady=(theme.PADDING_SMALL if row else 0, 2), sticky="w"
        )
        min_lines, max_lines = _body_limits(label, body)
        create_readonly_text(frame, text=body, min_lines=min_lines, max_lines=max_lines).grid(row=row * 2 + 1, column=0, sticky="we")
    return frame


def sections_from_value(payload: dict[str, Any]) -> list[tuple[str, str]]:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else None
    return _result_sections(result) if result is not None else _draft_sections(payload)


def _result_sections(response: dict[str, Any]) -> list[tuple[str, str]]:
    sections = [("Summary", _summary_text(response))]
    changed = _list_text(
        response.get("changed_source_files")
        or response.get("changed_assets")
    )
    if changed:
        label = "Changed Source Files" if response.get("changed_source_files") else "Changed Assets"
        sections.append((label, changed))
    sections.append(("Release Fingerprint Delta", _fingerprint_text(response)))
    sections.append(("Effects", _effects_text(response)))
    sections.append(("Validation Risks", _list_text(response.get("validation_risks"))))
    sections.append(("Artifacts", _artifact_text(response.get("artifacts"))))
    sections.append(("Required Fields", _list_text(response.get("required_fields"))))
    sections.append(("Existing References", _list_text(response.get("references_existing_codes"))))
    return [(label, body) for label, body in sections if body]


def _draft_sections(payload: dict[str, Any]) -> list[tuple[str, str]]:
    sections = [
        ("Current Summary", _mapping_text(payload.get("current_summary") or payload.get("current"))),
        ("Draft Summary", _mapping_text(payload.get("draft_summary") or payload.get("draft"))),
        ("Diff", str(payload.get("diff") or "").strip()),
    ]
    return [(label, body) for label, body in sections if body]


def _summary_text(response: dict[str, Any]) -> str:
    lines = [str(response.get("headline") or "").strip()]
    lines.extend(str(item).strip() for item in response.get("summary_lines", ()) if str(item).strip())
    return "\n".join(line for line in lines if line)


def _fingerprint_text(response: dict[str, Any]) -> str:
    current = str(response.get("current_release_fingerprint") or "").strip()
    candidate = str(response.get("candidate_release_fingerprint") or "").strip()
    changed = response.get("release_fingerprint_changed")
    lines = []
    if current:
        lines.append(f"Current: {current}")
    if candidate:
        lines.append(f"Candidate: {candidate}")
    if changed not in (None, ""):
        lines.append(f"Changed: {bool(changed)}")
    return "\n".join(lines)


def _effects_text(response: dict[str, Any]) -> str:
    lines = []
    for key, label in (("compile_effect", "Compile"), ("prompt_effect", "Prompt"), ("corpus_effect", "Corpus")):
        value = str(response.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _artifact_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    lines = []
    for item in value:
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("value") or "").strip():
            lines.append(f"{item['label']}: {item['value']}")
    return "\n".join(lines)


def _mapping_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    return "\n".join(f"{key}: {_inline_value(item)}" for key, item in value.items() if _inline_value(item))


def _list_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    return "\n".join(str(item) for item in value if str(item).strip())


def _inline_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{key}={_inline_value(item)}" for key, item in value.items() if _inline_value(item)]
        return "; ".join(parts)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    return str(value or "").strip()


def _body_limits(label: str, body: str) -> tuple[int, int]:
    if label in {"Summary", "Diff"}:
        return (4, 12)
    return (2, 8)
