"""Curated document-level embedding text construction."""

from __future__ import annotations

import json
from typing import Any

from .common import as_optional_int, as_optional_text, compose_capped_sections, row_text
from .types import ExtractedFieldSource, ExtractedRowSource, PendingEmbeddingSource, PromotionSource


def build_inline_source(document_id: str, document: dict[str, Any]) -> PendingEmbeddingSource:
    classification = document.get("classification") if isinstance(document.get("classification"), dict) else {}
    context = document.get("context") if isinstance(document.get("context"), dict) else {}
    source = document.get("source") if isinstance(document.get("source"), dict) else {}
    content = document.get("content") if isinstance(document.get("content"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    return PendingEmbeddingSource(
        document_id=document_id,
        normalized_json=json.dumps(document, ensure_ascii=False),
        file_name=source.get("file_name"),
        file_path=source.get("file_path"),
        document_type=as_optional_text(classification.get("document_type")),
        page_count=as_optional_int(classification.get("page_count")),
        payload_free_text=as_optional_text(content.get("free_text")),
        promotions=tuple(_promotion_sources_from_document(document)),
        rows=tuple(
            ExtractedRowSource(
                row_id=None,
                row_index=index,
                row_json=json.dumps(row, ensure_ascii=False),
                source_ref=f"content.rows[{index}]",
            )
            for index, row in enumerate(rows)
            if isinstance(row, dict)
        ),
        fields=tuple(
            ExtractedFieldSource(field_id=None, key=str(key), value=str(value), source_ref=f"content.fields.{key}")
            for key, value in fields.items()
            if value is not None and not isinstance(value, (dict, list))
        ),
    )


def build_embedding_text(document: dict[str, Any], max_chars: int = 12000) -> str:
    classification = document.get("classification", {})
    context = document.get("context", {})
    content = document.get("content", {})
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    promotions = document.get("document_promotions") if isinstance(document.get("document_promotions"), list) else []
    sections = [
        _labeled_values(classification, (("document_type", "Typ"), ("category", "Kategorie"), ("subcategory", "Subkategorie"), ("language", "Sprache")), sep=" | "),
        "\n".join(_promotion_lines(promotions)),
        "\n".join(_list_section(context, key, label) for key, label in (("tags", "Tags"), ("people", "Personen"), ("organizations", "Organisationen")) if _list_section(context, key, label)),
        str(content.get("free_text") or "").strip(),
        "\n".join(
            f"{key}: {value}"
            for key, value in fields.items()
            if not str(key).startswith("_") and value is not None and not isinstance(value, (dict, list))
        ),
        "\n".join(row_text(row) for row in rows if isinstance(row, dict) and row_text(row)),
    ]
    return compose_capped_sections(sections, max_chars)


def _labeled_values(payload: dict[str, Any], keys: tuple[tuple[str, str], ...], *, sep: str = "\n") -> str:
    return sep.join(f"{label}: {payload[key]}" for key, label in keys if payload.get(key))


def _list_section(context: dict[str, Any], key: str, label: str) -> str:
    raw_values = context.get(key)
    if not isinstance(raw_values, list) or not raw_values:
        return ""
    values = []
    for raw_value in raw_values:
        if isinstance(raw_value, dict):
            values.append(str(raw_value.get("name") or raw_value.get("tag") or raw_value.get("value") or raw_value))
        else:
            values.append(str(raw_value))
    return f"{label}: {', '.join(values)}"


def _promotion_sources_from_document(document: dict[str, Any]) -> list[PromotionSource]:
    promotions = document.get("document_promotions") if isinstance(document.get("document_promotions"), list) else []
    sources: list[PromotionSource] = []
    for promotion in promotions:
        if not isinstance(promotion, dict) or not promotion.get("display_value") or not promotion.get("slot"):
            continue
        promotion_id = promotion.get("promotion_id")
        sources.append(
            PromotionSource(
                promotion_id=int(promotion_id) if isinstance(promotion_id, int) else None,
                slot=str(promotion["slot"]),
                slot_label=as_optional_text(promotion.get("slot_label")),
                value_type=as_optional_text(promotion.get("value_type")),
                query_role=as_optional_text(promotion.get("query_role")),
                display_value=str(promotion["display_value"]),
                source_path=as_optional_text(promotion.get("source_path")),
            )
        )
    return sources


def _promotion_lines(promotions: list[Any]) -> list[str]:
    lines: list[str] = []
    for promotion in promotions:
        if not isinstance(promotion, dict) or not promotion.get("display_value"):
            continue
        label = promotion.get("slot_label") or promotion.get("slot") or "promotion"
        role = promotion.get("query_role")
        prefix = f"{label} ({role})" if role else str(label)
        lines.append(f"{prefix}: {promotion['display_value']}")
    return lines
