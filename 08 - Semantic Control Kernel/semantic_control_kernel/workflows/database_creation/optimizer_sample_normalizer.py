from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence


def analyze_sample_input_from_optimizer_raw(
    *,
    sample_id: str,
    source_path: Path,
    raw_payloads: Sequence[Mapping[str, Any]],
    raw_extract_paths: Sequence[str],
) -> dict[str, Any]:
    first = dict(raw_payloads[0]) if raw_payloads else {}
    source = _source(first, source_path)
    profile = _profile(raw_payloads)
    return {
        "schema_version": "kernel.analyze_sample.input.v1",
        "sample_id": sample_id,
        "source_ref": {
            "kind": "interpreter_request_view_vision.v1" if profile == "vision" else "interpreter_request_view_file.v1",
            "ref": str(source_path.resolve(strict=False)),
            "raw_extract_paths": list(raw_extract_paths),
        },
        "route": {
            "ingestion_profile": profile,
            "interpreter_profile": profile,
            "input_modality": "scan_or_image" if profile == "vision" else "file",
            "is_scan": profile == "vision",
            "language": source.get("language") or "unknown",
        },
        "document": {
            "source": source,
            "context": _merged_context(raw_payloads),
            "extracted_content": {
                "summary": {},
                "sections": _sections(raw_payloads),
                "facts": {},
                "tables": _tables(raw_payloads),
            },
        },
        "completeness": {
            "semantic_content_complete": True,
            "prompt_budget_truncation_applied": False,
            "omitted_semantic_content": [],
            "notes": [],
        },
    }


def _source(first_payload: Mapping[str, Any], source_path: Path) -> dict[str, Any]:
    source_payload = first_payload.get("source")
    source = dict(source_payload) if isinstance(source_payload, Mapping) else {}
    return {
        "file_name": str(source.get("file_name") or source_path.name),
        "file_ext": str(source.get("file_ext") or source_path.suffix).lstrip("."),
        "content_hash": str(source.get("content_hash") or ""),
        "page_count": _int_value(source.get("page_count")) or 1,
        "document_type": str(source.get("document_type") or "unknown"),
        "language": str(source.get("language") or "unknown"),
        "size_bytes": source.get("size_bytes"),
        "created_at": source.get("created_at"),
        "modified_at": source.get("modified_at"),
        "is_scan": str(first_payload.get("optimizer_profile") or "").strip().lower() == "vision",
        "has_handwriting": bool(source.get("has_handwriting") or False),
    }


def _merged_context(raw_payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in raw_payloads:
        context = payload.get("context")
        if isinstance(context, Mapping):
            merged.update(dict(context))
    return merged


def _sections(raw_payloads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for payload in raw_payloads:
        for index, block in enumerate(_blocks(payload), start=1):
            value = _clean_text(block.get("value"))
            if value is None:
                continue
            position = _mapping(block.get("position"))
            page = _int_value(position.get("page")) or _context_page(payload) or 1
            role = _clean_text(block.get("layout_label")) or _clean_text(block.get("type")) or "body"
            key = (page, role, value)
            if key in seen:
                continue
            seen.add(key)
            sections.append(
                {
                    "id": _clean_text(block.get("id")) or f"section_{len(sections) + index:04d}",
                    "page": page,
                    "role": role,
                    "text": value,
                }
            )
    return sections


def _tables(raw_payloads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tables: dict[tuple[int, int], dict[str, Any]] = {}
    for payload in raw_payloads:
        for block in _blocks(payload):
            position = _mapping(block.get("position"))
            if block.get("type") != "cell" and "row" not in position and "col" not in position:
                continue
            page = _int_value(position.get("page")) or 1
            table_index = _int_value(position.get("table_index")) or 0
            row_index = _int_value(position.get("row")) or 0
            col_index = _int_value(position.get("col")) or 0
            table = tables.setdefault(
                (page, table_index),
                {"id": f"table_{page}_{table_index}", "page": page, "role": "observed_table", "headers": [], "rows": []},
            )
            while len(table["rows"]) <= row_index:
                table["rows"].append({"cells": {}})
            column = f"col_{col_index}"
            if column not in table["headers"]:
                table["headers"].append(column)
            table["rows"][row_index]["cells"][column] = str(block.get("value") or "")
    return list(tables.values())


def _blocks(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    reference = payload.get("ocr_reference")
    blocks = reference.get("blocks") if isinstance(reference, Mapping) else None
    return tuple(item for item in blocks or () if isinstance(item, Mapping))


def _profile(raw_payloads: Sequence[Mapping[str, Any]]) -> str:
    for payload in raw_payloads:
        profile = str(payload.get("optimizer_profile") or "").strip().lower()
        if profile == "vision":
            return "vision"
    return "file"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _int_value(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _context_page(payload: Mapping[str, Any]) -> int | None:
    context = payload.get("context")
    return _int_value(context.get("page_number")) if isinstance(context, Mapping) else None
