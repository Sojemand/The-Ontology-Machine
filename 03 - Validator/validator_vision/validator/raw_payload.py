"""Raw-payload page grouping helpers for raw block inspection."""
from __future__ import annotations

from typing import Any


def compact_pages_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reference = payload.get("ocr_reference")
    if not isinstance(reference, dict):
        return []
    blocks = reference.get("blocks")
    if not isinstance(blocks, list):
        return []
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    default_page = _int_value(context.get("page_number"), default=1)
    pages: dict[int, dict[str, Any]] = {}

    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("value") or "").strip()
        if not text:
            continue
        position = block.get("position") if isinstance(block.get("position"), dict) else {}
        page_no = _int_value(position.get("page"), default=default_page)
        page = pages.setdefault(page_no, {"page": page_no, "blocks": []})
        page["blocks"].append(text)

    return [pages[key] for key in sorted(pages)]


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = ["compact_pages_from_payload"]
