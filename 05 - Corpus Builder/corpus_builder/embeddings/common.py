"""Shared text helpers for embedding domain modules."""

from __future__ import annotations

import re
from typing import Any

WHITESPACE_RE = re.compile(r"\s+")
CHUNK_LABELS = {
    "segment": "Abschnitte",
    "free_text": "Freitext",
    "row": "Zeilen",
    "field": "Felder",
    "promotion": "Top-Level-Fakten",
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", str(value)).strip()


def first_non_empty(*values: object) -> str | None:
    for value in values:
        text = as_optional_text(value)
        if text:
            return text
    return None


def as_optional_text(value: object) -> str | None:
    text = clean_text(value)
    return text or None


def as_optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in row.items():
        if value is None or str(key).startswith("_") or isinstance(value, (dict, list)):
            continue
        parts.append(f"{key}: {value}")
    return " | ".join(parts)


def compose_capped_sections(sections: list[str], max_chars: int) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for section in sections:
        text = section.strip()
        if not text or remaining <= 0:
            continue
        separator = "\n\n" if chunks else ""
        budget = remaining - len(separator)
        if budget <= 0:
            break
        if len(text) <= budget:
            chunks.append(separator + text)
            remaining -= len(separator) + len(text)
            continue
        chunks.append(separator + text[:budget].rstrip())
        break
    return "".join(chunks).strip()


def chunk_char_cap(max_chars: int) -> int:
    try:
        normalized = int(max_chars)
    except (TypeError, ValueError):
        normalized = 700
    return max(1, min(normalized, 700))
