"""Raw Optimizer payload summarization for source sample inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .source_inspection_text import append_label_value, append_text, join_unique, limit_unique


def summarize_raw_payload(payload: dict[str, Any]) -> dict[str, Any]:
    headings: list[str] = []
    field_like: list[str] = []
    text_parts: list[str] = []
    collect_preferred_text(payload, text_parts, headings, field_like)
    if not text_parts:
        collect_any_interesting_text(payload, text_parts)
    return {
        "text": join_unique(text_parts),
        "headings": limit_unique(headings, limit=40),
        "field_like_phrases": limit_unique(field_like, limit=60),
    }


def collect_preferred_text(payload: Any, text_parts: list[str], headings: list[str], field_like: list[str]) -> None:
    if not isinstance(payload, dict):
        return
    source = payload.get("source")
    if isinstance(source, dict):
        for key in ("file_name", "document_type", "language"):
            append_label_value(field_like, key, source.get(key))
    context = payload.get("context")
    if isinstance(context, dict):
        for key, value in context.items():
            append_label_value(field_like, key, value)
    reference = payload.get("ocr_reference")
    if isinstance(reference, dict):
        blocks = reference.get("blocks")
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                append_text(headings, block.get("layout_label"))
                append_text(text_parts, block.get("value"))
    for key in ("source", "context", "ocr_reference"):
        collect_any_interesting_text(payload.get(key), text_parts)


def collect_any_interesting_text(value: Any, text_parts: list[str], *, parent_key: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in {"text", "value", "content", "free_text", "summary", "label", "title", "heading", "excerpt"}:
                append_text(text_parts, item)
            else:
                collect_any_interesting_text(item, text_parts, parent_key=key_text)
        return
    if isinstance(value, list):
        for item in value[:200]:
            collect_any_interesting_text(item, text_parts, parent_key=parent_key)
        return
    if isinstance(value, str) and parent_key.lower() in {"lines", "paragraphs", "items"}:
        append_text(text_parts, value)


def inspection_signals(
    source_path: Path,
    raw_payloads: list[dict[str, Any]],
    raw_extract_paths: list[Path],
    page_image_paths: list[Path],
) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "filename": source_path.name,
        "extension": source_path.suffix.lower(),
        "size_bytes": source_path.stat().st_size,
        "raw_extract_count": len(raw_extract_paths),
        "page_image_count": len(page_image_paths),
    }
    first = raw_payloads[0] if raw_payloads else {}
    if first:
        signals["optimizer_profile"] = str(first.get("optimizer_profile") or "")
        ctx = first.get("context") if isinstance(first.get("context"), dict) else {}
        source = first.get("source") if isinstance(first.get("source"), dict) else {}
        signals["detected_language"] = str(source.get("language") or "")
        signals["estimated_document_type"] = str(source.get("document_type") or "")
        if ctx.get("document_page_count") is not None:
            signals["document_page_count"] = ctx.get("document_page_count")
    return signals
