"""Readable review-result rendering for operation previews."""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from . import theme
from .text_widgets import create_readonly_text


def render(parent, surface):
    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    for row, (label, body) in enumerate(sections_from_response((surface.value or {}).get("result") or {})):
        create_readonly_text(frame, text=label, font=theme.font_small(), text_color=theme.COLOR_MUTED).grid(
            row=row * 2, column=0, pady=(theme.PADDING_SMALL if row else 0, 2), sticky="w"
        )
        min_lines, max_lines = _body_limits(label, body)
        create_readonly_text(frame, text=body, min_lines=min_lines, max_lines=max_lines).grid(row=row * 2 + 1, column=0, sticky="we")
    return frame


def sections_from_response(response: dict[str, Any]) -> list[tuple[str, str]]:
    review = response.get("review_payload") if isinstance(response.get("review_payload"), dict) else {}
    sections = [("Summary", _summary_text(response))]
    sections.extend(
        [
            ("Input Summary", _mapping_text(review.get("input_summary"))),
            ("Release Summary", _mapping_text(review.get("release_summary"))),
            ("Projection Suggestions", _projection_text(review.get("projection_suggestions"))),
            ("Master Term Suggestions", _master_term_text(review.get("master_term_suggestions"))),
            ("Applied Source Changes", _applied_text(response.get("applied_changes"))),
            ("Preview Delta", _preview_delta_text(response)),
            ("Routing Review", _routing_text(review.get("routing_review"))),
            ("Document Comparison", _document_comparison_text(review.get("document_comparison"))),
            ("Behalten / Verdichtet / Verloren", _balance_text(review.get("information_balance"))),
            ("Warnings", _list_text(review.get("warnings"))),
            ("Next Steps", _list_text(review.get("next_steps"))),
        ]
    )
    return [(label, body) for label, body in sections if body]


def _summary_text(response: dict[str, Any]) -> str:
    lines = [str(response.get("headline") or "").strip()]
    summary_lines = response.get("summary_lines")
    if isinstance(summary_lines, list):
        lines.extend(str(item).strip() for item in summary_lines if str(item).strip())
    return "\n".join(line for line in lines if line)


def _mapping_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    return "\n".join(f"{key}: {_inline_value(item)}" for key, item in value.items() if _inline_value(item))


def _projection_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        badge = "[recommended] " if item.get("recommended") else ""
        score = f" | score {item.get('score')}" if item.get("score") not in (None, "") else ""
        lines.append(f"{badge}{item.get('projection_id') or '-'} | {item.get('action') or 'review'} | {item.get('label') or ''}{score}".strip())
        reason = str(item.get("reason") or "").strip()
        if reason:
            lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _master_term_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        lines.append(f"{item.get('suggestion_type') or 'review'} | {item.get('section_id') or '-'}::{item.get('term_id') or '-'} | {item.get('label') or ''}".strip())
        reason = str(item.get("reason") or "").strip()
        if reason:
            lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _routing_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    lines = _mapping_text({key: item for key, item in value.items() if key != "candidate_rankings" and key != "warnings"}).splitlines()
    rankings = value.get("candidate_rankings")
    if isinstance(rankings, list) and rankings:
        lines.append("Candidate rankings:")
        for item in rankings[:3]:
            if isinstance(item, dict):
                lines.append(f"{item.get('projection_id') or '-'} | score {item.get('score')} | {', '.join(str(signal) for signal in item.get('signals', [])[:3])}")
    warnings = value.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("Routing warnings:")
        lines.extend(str(item) for item in warnings if str(item).strip())
    return "\n".join(line for line in lines if line)


def _applied_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        parts = [str(item.get("action") or "-"), str(item.get("target") or "-")]
        source = str(item.get("source") or "").strip()
        if source:
            parts.append(source)
        lines.append(" | ".join(parts))
        reason = str(item.get("reason") or "").strip()
        if reason:
            lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _preview_delta_text(response: dict[str, Any]) -> str:
    lines = _list_text(
        response.get("changed_source_files")
        or response.get("changed_assets")
    ).splitlines()
    current = str(response.get("current_release_fingerprint") or "").strip()
    candidate = str(response.get("candidate_release_fingerprint") or "").strip()
    if current:
        lines.append(f"Current fingerprint: {current}")
    if candidate:
        lines.append(f"Candidate fingerprint: {candidate}")
    if response.get("release_fingerprint_changed") not in (None, ""):
        lines.append(f"Fingerprint changed: {bool(response.get('release_fingerprint_changed'))}")
    return "\n".join(line for line in lines if line)


def _document_comparison_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    lines: list[str] = []
    for key in ("original", "structured", "normalized"):
        item = value.get(key)
        if not isinstance(item, dict):
            continue
        lines.append(key.title())
        for field, field_value in item.items():
            text = _inline_value(field_value)
            if text:
                lines.append(f"{field}: {text}")
    return "\n".join(lines)


def _balance_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    labels = {"kept": "Behalten", "condensed": "Verdichtet", "lost": "Verloren"}
    return "\n".join(f"{labels[key]}: {', '.join(str(item) for item in value.get(key, []) if str(item).strip()) or '-'}" for key in ("kept", "condensed", "lost"))


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
    text = str(value or "").strip()
    return text


def _body_limits(label: str, body: str) -> tuple[int, int]:
    if label in {"Summary", "Document Comparison"}:
        return (4, 12)
    if label in {"Projection Suggestions", "Master Term Suggestions", "Routing Review"}:
        return (3, 12)
    return (2, 8)
