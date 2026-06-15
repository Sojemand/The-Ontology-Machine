"""Source decoding helpers for embedding chunk construction."""

from __future__ import annotations

import json
import re
from typing import Any

from .common import as_optional_text, clean_text
from .types import ExtractedFieldSource, ExtractedRowSource


def decode_row_json(row_json: str) -> dict[str, Any] | None:
    try:
        data = json.loads(row_json)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def content_free_text(document: dict[str, Any]) -> str | None:
    content = document.get("content") if isinstance(document.get("content"), dict) else {}
    return as_optional_text(content.get("free_text"))


def inline_row_sources(document: dict[str, Any]) -> list[ExtractedRowSource]:
    content = document.get("content") if isinstance(document.get("content"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    return [
        ExtractedRowSource(
            row_id=None,
            row_index=index,
            row_json=json.dumps(row, ensure_ascii=False),
            source_ref=f"content.rows[{index}]",
        )
        for index, row in enumerate(rows)
        if isinstance(row, dict)
    ]


def inline_field_sources(document: dict[str, Any]) -> list[ExtractedFieldSource]:
    content = document.get("content") if isinstance(document.get("content"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    return [
        ExtractedFieldSource(field_id=None, key=str(key), value=str(value), source_ref=f"content.fields.{key}")
        for key, value in fields.items()
        if value is not None and not isinstance(value, (dict, list))
    ]


def split_long_text(text: str, *, body_budget: int) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    max_len = max(1, body_budget)
    if len(cleaned) <= max_len:
        return [cleaned]
    parts = [part.strip() for part in re.split(r"(?:\n\s*\n+|(?<=[.!?])\s+)", cleaned) if part.strip()] or [cleaned]
    chunks: list[str] = []
    bucket = ""
    for part in parts:
        candidate = f"{bucket} {part}".strip() if bucket else part
        if bucket and len(candidate) > max_len:
            chunks.append(bucket)
            bucket = part
            continue
        if len(candidate) <= max_len:
            bucket = candidate
            continue
        if bucket:
            chunks.append(bucket)
            bucket = ""
        bucket = _append_long_part(chunks, part, max_len)
    if bucket:
        chunks.append(bucket)
    return [chunk for chunk in chunks if chunk]


def page_from_row_source(row_source: ExtractedRowSource, file_path: str | None) -> int | None:
    return page_from_file_path(file_path)


def page_from_file_path(file_path: str | None) -> int | None:
    if not file_path:
        return None
    match = re.search(r"::page=(\d+)-of-\d+$", str(file_path), flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _append_long_part(chunks: list[str], part: str, max_len: int) -> str:
    remainder = part
    while len(remainder) > max_len:
        cut = remainder.rfind(" ", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        chunks.append(remainder[:cut].rstrip())
        remainder = remainder[cut:].strip()
    return remainder
