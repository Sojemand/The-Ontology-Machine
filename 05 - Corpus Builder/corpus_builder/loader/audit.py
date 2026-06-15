"""Evidence and audit helpers for the loader pipeline."""

from __future__ import annotations

import json
import re
from typing import Any

from ..models.serialization import now_iso
from ..semantic_release import projection_metadata
from .policy import compact_search_text, detect_field_type, extract_currency, normalize_date_value, normalize_search_text, normalize_source_refs
from .types import JsonDict


def _derive_page_from_refs(source_refs: list[str], page_count: int | None) -> int | None:
    for source_ref in source_refs:
        match = re.search(r"page[_-]?(\d+)", source_ref, flags=re.IGNORECASE) or re.search(r"^p(?:age)?(\d+)", source_ref, flags=re.IGNORECASE)
        if match and 1 <= int(match.group(1)) <= max(1, page_count or int(match.group(1))):
            return int(match.group(1))
    return None


def _preview_value(value: Any, *, max_items: int = 6, max_length: int = 280) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        parts = [f"{key}: {_preview_value(child, max_items=max_items, max_length=max_length) if isinstance(child, (dict, list)) else child}" for key, child in value.items() if not str(key).startswith("_") and child is not None][:max_items]
        preview = " | ".join(part for part in parts if part and not part.endswith(": None"))
    elif isinstance(value, list):
        parts = [_preview_value(item, max_items=max_items, max_length=max_length) if isinstance(item, (dict, list)) else str(item) for item in value[:max_items] if item is not None]
        preview = " | ".join(part for part in parts if part)
    else:
        preview = str(value).strip()
    preview = re.sub(r"\s+", " ", preview or "").strip()
    return preview[: max_length - 3] + "..." if preview and len(preview) > max_length else preview or None


def _atom_type_for_path(json_path: str) -> str:
    if "._source_refs." in json_path or json_path.endswith("source_ref") or ".source_refs[" in json_path:
        return "source_ref"
    for prefix, atom_type in (("content.fields.", "field"), ("content.rows[", "row_cell"), ("context.", "context"), ("classification.", "classification"), ("projection.", "projection"), ("relations[", "relation"), ("source.", "source"), ("processing.", "processing")):
        if json_path.startswith(prefix):
            return atom_type
    if json_path.startswith("content.segments["):
        return "segment"
    return "free_text" if json_path == "content.free_text" else "generic"


_FIELD_PATH_RE = re.compile(r"^content\.fields\.([^.\[\]]+)(?:\.|\[|$)")
_ROW_PATH_RE = re.compile(r"^content\.rows\[(\d+)\](?:\.|\[|$)")
_SEGMENT_PATH_RE = re.compile(r"^content\.segments\[(\d+)\](?:\.|\[|$)")
_RELATION_PATH_RE = re.compile(r"^relations\[(\d+)\](?:\.|\[|$)")


def _anchor_from_path(
    json_path: str,
    value: Any,
    *,
    row_index: int | None = None,
    fallback: tuple[str | None, str | None] = (None, None),
) -> tuple[str | None, str | None]:
    segment = _SEGMENT_PATH_RE.match(json_path)
    if segment:
        segment_id = str(value.get("segment_id") or "").strip() if isinstance(value, dict) else ""
        if not segment_id and fallback[0] == "segment" and fallback[1]:
            return fallback
        return "segment", f"segment:{segment_id or segment.group(1)}"
    row = _ROW_PATH_RE.match(json_path)
    if row:
        return "row", f"row:{row_index if row_index is not None else row.group(1)}"
    field = _FIELD_PATH_RE.match(json_path)
    if field and field.group(1) != "_source_refs":
        return "field", f"field:{field.group(1)}"
    relation = _RELATION_PATH_RE.match(json_path)
    if relation:
        return "relation", f"relation:{relation.group(1)}"
    return fallback


def _source_ref_anchor(
    json_path: str,
    ref_key: str,
    *,
    row_index: int | None,
    fallback: tuple[str | None, str | None],
) -> tuple[str | None, str | None]:
    if json_path == "content.fields":
        return "field", f"field:{ref_key}"
    row = _ROW_PATH_RE.match(json_path)
    if row or row_index is not None:
        return "row", f"row:{row_index if row_index is not None else row.group(1)}"
    return fallback


def build_evidence_atoms(payload: JsonDict, *, page_count: int | None) -> list[JsonDict]:
    atoms: list[JsonDict] = []

    def visit(
        value: Any,
        json_path: str,
        *,
        row_index: int | None = None,
        column_key: str | None = None,
        context_label: str | None = None,
        parent_preview: str | None = None,
        source_refs: list[str] | None = None,
        anchor_kind: str | None = None,
        anchor_key: str | None = None,
    ) -> None:
        active_refs = list(dict.fromkeys(source_refs or []))
        active_anchor = _anchor_from_path(json_path, value, row_index=row_index, fallback=(anchor_kind, anchor_key))
        if isinstance(value, dict):
            local_refs = value.get("_source_refs") if isinstance(value.get("_source_refs"), dict) else {}
            for key, refs in local_refs.items():
                for ref_index, ref in enumerate(normalize_source_refs(refs)):
                    ref_anchor = _source_ref_anchor(json_path, str(key), row_index=row_index, fallback=active_anchor)
                    atoms.append({"atom_type": "source_ref", "json_path": f"{json_path}._source_refs.{key}[{ref_index}]", "anchor_kind": ref_anchor[0], "anchor_key": ref_anchor[1], "page": _derive_page_from_refs([ref], page_count), "row_index": row_index, "column_key": str(key), "source_ref": ref, "text_value": ref, "normalized_text": normalize_search_text(ref), "compact_text": compact_search_text(ref), "numeric_value": None, "date_value": None, "currency": None, "context_label": str(key), "context_window": parent_preview or _preview_value(value)})
            preview = _preview_value(value)
            for key, child in value.items():
                if not str(key).startswith("_"):
                    next_column = str(key) if row_index is not None and column_key is None else column_key
                    child_path = f"{json_path}.{key}" if json_path else str(key)
                    child_anchor = _anchor_from_path(child_path, child, row_index=row_index, fallback=active_anchor)
                    visit(child, child_path, row_index=row_index, column_key=next_column, context_label=str(key), parent_preview=preview, source_refs=list(dict.fromkeys(active_refs + normalize_source_refs(local_refs.get(key)))), anchor_kind=child_anchor[0], anchor_key=child_anchor[1])
            return
        if isinstance(value, list):
            preview = _preview_value(value)
            for index, item in enumerate(value):
                item_path = f"{json_path}[{index}]"
                item_row_index = index if json_path == "content.rows" else row_index
                item_anchor = _anchor_from_path(item_path, item, row_index=item_row_index, fallback=active_anchor)
                visit(item, item_path, row_index=item_row_index, column_key=column_key, context_label=context_label, parent_preview=preview, source_refs=active_refs, anchor_kind=item_anchor[0], anchor_key=item_anchor[1])
            return
        if value is None:
            return
        value_type, numeric_value = detect_field_type(json_path.rsplit(".", 1)[-1], value)
        atoms.append({"atom_type": _atom_type_for_path(json_path), "json_path": json_path, "anchor_kind": active_anchor[0], "anchor_key": active_anchor[1], "page": _derive_page_from_refs(active_refs, page_count), "row_index": row_index, "column_key": column_key, "source_ref": active_refs[0] if active_refs else None, "text_value": str(value), "normalized_text": normalize_search_text(value), "compact_text": compact_search_text(value), "numeric_value": numeric_value, "date_value": normalize_date_value(value) if value_type == "date" or isinstance(value, str) else None, "currency": extract_currency(value) if value_type == "currency" or isinstance(value, str) else None, "context_label": context_label, "context_window": parent_preview or _preview_value(value)})

    visit(payload, "")
    return [atom for atom in atoms if atom["json_path"]]


def fallback_materialization(*, document_id: str, payload: JsonDict, release: JsonDict | None, reason: str, source_mode: str) -> JsonDict:
    projection_meta = projection_metadata(payload) if isinstance(payload, dict) else {}
    return {
        "projection_id": str(projection_meta.get("projection_id") or ""),
        "projection_fingerprint": str(projection_meta.get("projection_fingerprint") or ""),
        "document_promotions": [],
        "slot_candidates": [],
        "entities": [],
        "entity_attributes": [],
        "entity_relations": [],
        "processing_state": {
            "document_id": document_id, "schema_version": str(payload.get("schema_version") or "") if isinstance(payload, dict) else "",
            "materialization_version": str(release.get("materialization_version") or "") if isinstance(release, dict) else "",
            "projection_id": str(projection_meta.get("projection_id") or ""), "projection_fingerprint": str(projection_meta.get("projection_fingerprint") or ""),
            "materialization_state": "stale", "stale_reason": reason, "source_mode": source_mode, "last_materialized_at": now_iso(),
        },
        "audits": [{"level": "error", "code": "materialization_failed", "document_id": document_id, "projection_id": str(projection_meta.get("projection_id") or ""), "message": reason, "details_json": json.dumps({"projection_id": projection_meta.get("projection_id"), "source_mode": source_mode}, ensure_ascii=False)}],
    }


__all__ = ["build_evidence_atoms", "fallback_materialization"]
