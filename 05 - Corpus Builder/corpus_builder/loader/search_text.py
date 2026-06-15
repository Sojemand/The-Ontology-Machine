"""Search text shaping for the loader domain."""

from __future__ import annotations

from .policy import is_non_empty
from .types import JsonDict


def _row_text(row: JsonDict) -> str:
    return " ".join(
        str(value)
        for key, value in row.items()
        if not str(key).startswith("_") and value is not None and not isinstance(value, (dict, list))
    ).strip()


def _segment_text(segment: JsonDict) -> str:
    parts: list[str] = []
    for key in ("section", "label", "text"):
        value = segment.get(key)
        if is_non_empty(value):
            parts.append(str(value))
    return " ".join(parts).strip()


def _promotion_texts(promotions: list[JsonDict] | None) -> list[str]:
    parts: list[str] = []
    for promotion in promotions or []:
        if not isinstance(promotion, dict):
            continue
        value = promotion.get("display_value")
        if not is_non_empty(value):
            continue
        label = promotion.get("slot_label") or promotion.get("slot") or "promotion"
        role = promotion.get("query_role")
        prefix = f"{label} ({role})" if is_non_empty(role) else str(label)
        parts.append(f"{prefix}: {value}")
    return parts


def build_fallback_search_text(
    doc: JsonDict,
    fields: JsonDict,
    rows: list[JsonDict],
    segments: list[JsonDict],
    tags: list[str],
    people: list[str],
    orgs: list[str],
    promotions: list[JsonDict] | None = None,
) -> str:
    parts: list[str] = []
    parts += [f"Tags: {', '.join(tags)}"] if tags else []
    parts += [f"People: {', '.join(people)}"] if people else []
    parts += [f"Organizations: {', '.join(orgs)}"] if orgs else []
    promotion_parts = _promotion_texts(promotions)
    field_parts = [f"{key}: {value}" for key, value in fields.items() if value is not None and not isinstance(value, (dict, list))]
    row_parts = [text for text in (_row_text(row) for row in rows) if text]
    segment_parts = [text for text in (_segment_text(segment) for segment in segments) if text]
    return "\n".join(
        parts
        + ([f"Promotions: {' | '.join(promotion_parts)}"] if promotion_parts else [])
        + ([f"Fields: {' | '.join(field_parts)}"] if field_parts else [])
        + ([f"Rows: {' || '.join(row_parts)}"] if row_parts else [])
        + ([f"Segments: {' || '.join(segment_parts)}"] if segment_parts else [])
    ).strip()


def build_fts_fields_text(
    doc: JsonDict,
    fields: JsonDict,
    rows: list[JsonDict],
    segments: list[JsonDict],
    promotions: list[JsonDict] | None = None,
) -> str:
    promotion_parts = _promotion_texts(promotions)
    field_parts = [f"{key}: {value}" for key, value in fields.items() if value is not None and not isinstance(value, (dict, list))]
    row_parts = [f"row_{index + 1}: {text}" for index, text in enumerate(_row_text(row) for row in rows) if text]
    segment_parts = [f"segment_{index + 1}: {text}" for index, text in enumerate(_segment_text(segment) for segment in segments) if text]
    return " | ".join(promotion_parts + field_parts + row_parts + segment_parts)


__all__ = ["build_fallback_search_text", "build_fts_fields_text"]
