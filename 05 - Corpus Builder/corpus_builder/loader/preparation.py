"""Preparation stage for loader payload shaping."""

from __future__ import annotations

from .review_policy import derive_field_provenance
from .preparation_lists import merge_name_lists, normalize_name_list, preferred_name_list
from .types import JsonDict, PreparedBundle
from .policy import is_non_empty
from .validation import default_validation_report


def _mapping_block(payload: JsonDict, key: str) -> JsonDict:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def content_fields(payload: JsonDict) -> JsonDict:
    fields = _mapping_block(_mapping_block(payload, "content"), "fields")
    return fields if isinstance(fields, dict) else {}


def content_rows(payload: JsonDict) -> list[JsonDict]:
    rows = _mapping_block(payload, "content").get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def content_segments(payload: JsonDict) -> list[JsonDict]:
    segments = _mapping_block(payload, "content").get("segments")
    return [segment for segment in segments if isinstance(segment, dict)] if isinstance(segments, list) else []


def content_free_text(payload: JsonDict) -> str | None:
    free_text = _mapping_block(payload, "content").get("free_text")
    return str(free_text) if is_non_empty(free_text) else None


def preferred_search_payload(structured_json: JsonDict, normalized_json: JsonDict | None) -> JsonDict:
    return normalized_json if isinstance(normalized_json, dict) else structured_json


def _first_non_empty(mapping: JsonDict, *keys: str):
    lowered = {str(key).lower(): key for key in mapping}
    for key in keys:
        actual = key if key in mapping else lowered.get(key.lower())
        if actual is not None and is_non_empty(mapping.get(actual)):
            return mapping[actual]
    return None


def prefer_mapping_value(primary: JsonDict, fallback: JsonDict, *keys: str):
    value = _first_non_empty(primary, *keys)
    return value if value is not None else _first_non_empty(fallback, *keys)


def _drop_internal_keys(value, *, keep_internal: frozenset[str] = frozenset()):
    if isinstance(value, dict):
        return {
            key: _drop_internal_keys(child, keep_internal=keep_internal)
            for key, child in value.items()
            if not str(key).startswith("_") or str(key) in keep_internal
        }
    return [_drop_internal_keys(item, keep_internal=keep_internal) for item in value] if isinstance(value, list) else value


def _sanitize_fields(fields: object) -> JsonDict:
    return _drop_internal_keys(fields) if isinstance(fields, dict) else {}


def _sanitize_rows(rows: object) -> list[JsonDict]:
    if not isinstance(rows, list):
        return []
    keep_internal = frozenset(("_row_type", "_row_index"))
    return [_drop_internal_keys(row, keep_internal=keep_internal) for row in rows if isinstance(row, dict)]


def _sanitize_segments(segments: object) -> list[JsonDict]:
    return [_drop_internal_keys(segment) for segment in segments if isinstance(segment, dict)] if isinstance(segments, list) else []


def _merge_public_mappings(primary: JsonDict, fallback: JsonDict) -> JsonDict:
    return dict(fallback, **primary) if primary else dict(fallback)


def _merge_public_rows(primary: list[JsonDict], fallback: list[JsonDict]) -> list[JsonDict]:
    if not primary:
        return list(fallback)
    rows: list[JsonDict] = []
    for index in range(max(len(primary), len(fallback))):
        primary_row = primary[index] if index < len(primary) else None
        fallback_row = fallback[index] if index < len(fallback) else None
        if primary_row is None and fallback_row is not None:
            rows.append(dict(fallback_row))
        elif fallback_row is None and primary_row is not None:
            rows.append(dict(primary_row))
        elif primary_row is not None and fallback_row is not None:
            rows.append(dict(fallback_row, **primary_row))
    return rows


def _preferred_name_list(preferred_json: JsonDict, fallback_json: JsonDict, key: str) -> list[str]:
    return preferred_name_list(preferred_json, fallback_json, key, lambda payload: _mapping_block(payload, "context"))


def _preferred_relations_source(preferred_json: JsonDict, fallback_json: JsonDict) -> list[JsonDict]:
    preferred = preferred_json.get("relations")
    fallback = fallback_json.get("relations")
    preferred_items = [item for item in preferred if isinstance(item, dict)] if isinstance(preferred, list) else []
    fallback_items = [item for item in fallback if isinstance(item, dict)] if isinstance(fallback, list) else []
    merged: list[JsonDict] = []
    seen: set[str] = set()
    for item in [*preferred_items, *fallback_items]:
        marker = repr(sorted(item.items()))
        if marker not in seen:
            seen.add(marker)
            merged.append(item)
    return merged


def _preferred_segments_source(preferred_json: JsonDict, fallback_json: JsonDict) -> list[JsonDict]:
    preferred = content_segments(preferred_json)
    return preferred if preferred else content_segments(fallback_json)


def _build_bundle(
    structured_json: JsonDict | None,
    normalized_json: JsonDict | None,
    validation_report: JsonDict | None,
    *,
    merge_evidence: bool,
    merge_lists: bool,
) -> PreparedBundle:
    structured_payload = structured_json if isinstance(structured_json, dict) else {}
    preferred_json = preferred_search_payload(structured_payload, normalized_json)
    validation_payload = validation_report if isinstance(validation_report, dict) else default_validation_report()
    evidence_payload = structured_payload or preferred_json
    preferred_fields = _sanitize_fields(content_fields(preferred_json))
    structured_fields = _sanitize_fields(content_fields(evidence_payload))
    preferred_rows = _sanitize_rows(content_rows(preferred_json))
    structured_rows = _sanitize_rows(content_rows(evidence_payload))
    sanitized_segments = _sanitize_segments(_preferred_segments_source(preferred_json, structured_payload))
    tags, people, orgs = (
        _preferred_name_list(preferred_json, structured_payload, name)
        for name in ("tags", "people", "organizations")
    )
    if merge_lists:
        context = _mapping_block(structured_payload, "context")
        tags = merge_name_lists(tags, normalize_name_list(context.get("tags"), "tags"))
        people = merge_name_lists(people, normalize_name_list(context.get("people"), "people"))
        orgs = merge_name_lists(orgs, normalize_name_list(context.get("organizations"), "organizations"))
    return PreparedBundle(
        structured_payload=structured_payload,
        preferred_json=preferred_json,
        validation_payload=validation_payload,
        source_mode="normalized" if isinstance(normalized_json, dict) else "structured",
        evidence_payload=evidence_payload,
        field_provenance=derive_field_provenance(content_fields(evidence_payload), validation_payload) if merge_evidence else {},
        structured_fields=structured_fields,
        sanitized_fields=_merge_public_mappings(preferred_fields, structured_fields) if merge_evidence else preferred_fields,
        sanitized_rows=_merge_public_rows(preferred_rows, structured_rows) if merge_evidence else preferred_rows,
        sanitized_segments=sanitized_segments,
        sanitized_relations=_drop_internal_keys(_preferred_relations_source(preferred_json, structured_payload)),
        tags=tags,
        people=people,
        orgs=orgs,
    )


def prepare_load_bundle(
    structured_json: JsonDict | None,
    normalized_json: JsonDict | None,
    validation_report: JsonDict | None,
) -> PreparedBundle:
    return _build_bundle(structured_json, normalized_json, validation_report, merge_evidence=True, merge_lists=True)


def prepare_rematerialize_bundle(structured_json: JsonDict | None, normalized_json: JsonDict | None) -> PreparedBundle:
    return _build_bundle(structured_json, normalized_json, None, merge_evidence=False, merge_lists=False)


def select_candidate_payload(preferred_json: JsonDict, structured_json: JsonDict) -> JsonDict:
    if not isinstance(preferred_json.get("projection"), dict) and isinstance(structured_json.get("projection"), dict):
        return structured_json
    return preferred_json


__all__ = [
    "content_fields",
    "content_free_text",
    "content_rows",
    "content_segments",
    "prefer_mapping_value",
    "prepare_load_bundle",
    "prepare_rematerialize_bundle",
    "preferred_search_payload",
    "select_candidate_payload",
]
