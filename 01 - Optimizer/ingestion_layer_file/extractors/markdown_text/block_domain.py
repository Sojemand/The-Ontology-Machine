"""Shared block factories for the markdown/text extractor."""
from __future__ import annotations

from typing import Any


def build_position(idx: int) -> dict[str, Any]:
    return {
        "sheet": None,
        "row": None,
        "col": None,
        "col_letter": None,
        "page": None,
        "paragraph_index": idx,
        "table_index": None,
    }


def make_text_block(block_id: str, block_type: str, idx: int, value: str) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": block_type,
        "position": build_position(idx),
        "value": value,
        "value_type": "text",
        "formatting": None,
        "confidence": None,
    }


def make_header_block(block_id: str, idx: int, value: str, heading_level: int) -> dict[str, Any]:
    return {
        "id": block_id,
        "type": "header",
        "position": build_position(idx),
        "value": value,
        "value_type": "text",
        "formatting": {"bold": True, "font_size": None, "heading_level": heading_level},
        "confidence": None,
    }
