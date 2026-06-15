"""Structured-payload claim collection for numeric/date validation."""
from __future__ import annotations

import math
from typing import Any

from .numeric_claim_parsing import iter_embedded_claims, iter_scalar_claims

_STRUCTURED_VALUE_SKIP_KEYS = frozenset({"segment_id", "page", "sequence", "confidence"})
_CONTEXT_SKIP_KEYS = frozenset({"source_document_path", "page_source_path", "projection_hint"})
_EMBEDDED_CONTEXT_HINT_KEYS = (
    "address",
    "anschrift",
    "street",
    "strasse",
    "straße",
    "postal",
    "zip",
    "plz",
    "phone",
    "telephone",
    "telefon",
    "fax",
    "iban",
    "bic",
    "hrb",
    "tax",
    "steuer",
    "number",
    "nummer",
    "reference",
    "referenz",
)


def collect_structured_claims(payload: dict[str, Any]) -> tuple[list[float], set[str]]:
    numbers: list[float] = []
    dates: set[str] = set()
    if not isinstance(payload, dict):
        return numbers, dates

    context = payload.get("context")
    if isinstance(context, dict):
        _collect_context_claims(context, "context", numbers, dates)

    content = payload.get("content")
    if not isinstance(content, dict):
        return numbers, dates

    _collect_embedded_claim_sets(content.get("fields"), "content.fields", numbers, dates)
    _collect_embedded_claim_sets(content.get("rows"), "content.rows", numbers, dates)
    _collect_embedded_claim_sets(content.get("free_text"), "content.free_text", numbers, dates)
    _collect_segment_text_claims(content.get("segments"), numbers, dates)
    return numbers, dates


def _collect_context_claims(value: Any, field_path: str, numbers: list[float], dates: set[str]) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).startswith("_") or key in _STRUCTURED_VALUE_SKIP_KEYS or key in _CONTEXT_SKIP_KEYS:
                continue
            _collect_context_claims(child, f"{field_path}.{key}", numbers, dates)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_context_claims(child, f"{field_path}[{index}]", numbers, dates)
        return
    _collect_scalar_claim_sets(value, numbers, dates)
    if isinstance(value, str) and _should_collect_embedded_context_claims(field_path, value):
        _collect_embedded_claim_set_from_value(value, field_path, numbers, dates)


def _collect_embedded_claim_sets(value: Any, field_path: str, numbers: list[float], dates: set[str]) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).startswith("_") or key in _STRUCTURED_VALUE_SKIP_KEYS:
                continue
            _collect_embedded_claim_sets(child, f"{field_path}.{key}", numbers, dates)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_embedded_claim_sets(child, f"{field_path}[{index}]", numbers, dates)
        return
    _collect_embedded_claim_set_from_value(value, field_path, numbers, dates)


def _collect_segment_text_claims(segments: Any, numbers: list[float], dates: set[str]) -> None:
    if not isinstance(segments, list):
        return
    for index, segment in enumerate(segments):
        if isinstance(segment, dict):
            _collect_embedded_claim_set_from_value(segment.get("text"), f"content.segments[{index}].text", numbers, dates)


def _collect_scalar_claim_sets(value: Any, numbers: list[float], dates: set[str]) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            numbers.append(float(value))
        return
    if isinstance(value, str):
        for candidate in iter_scalar_claims(value):
            if candidate.kind == "number":
                numbers.append(float(candidate.raw_value))
            else:
                dates.add(str(candidate.raw_value))


def _collect_embedded_claim_set_from_value(value: Any, field_path: str, numbers: list[float], dates: set[str]) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            numbers.append(float(value))
        return
    if isinstance(value, str):
        for candidate in iter_embedded_claims(value, context_hint=field_path):
            if candidate.kind == "number":
                numbers.append(float(candidate.raw_value))
            else:
                dates.add(str(candidate.raw_value))


def _should_collect_embedded_context_claims(field_path: str, value: str) -> bool:
    context = f"{field_path} {value}".lower()
    return any(key in context for key in _EMBEDDED_CONTEXT_HINT_KEYS)


__all__ = ["collect_structured_claims"]
