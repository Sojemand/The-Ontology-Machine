"""Cross-module normalization and identity helpers for semantic artifacts."""
from __future__ import annotations

import hashlib
import json
from typing import Any

_SCALAR_SETLIKE_KEYS = frozenset(
    {
        "aliases",
        "allowed_categories",
        "allowed_subcategories",
        "available_locales",
        "backward_compatible_with",
        "domain_ids",
        "domains",
        "evidence_paths",
        "example_document_types",
        "extends",
        "include_categories",
        "include_cell_codes",
        "include_document_types",
        "include_field_codes",
        "include_row_types",
        "include_subcategories",
        "party_roles",
        "projection_ids",
        "recommended_cell_codes",
        "section_roles",
        "source_paths",
        "text_markers",
    }
)
_OBJECT_LIST_SORT_KEYS = {
    "categories": "code",
    "cell_codes": "code",
    "document_types": "code",
    "domains": "id",
    "entity_types": "code",
    "field_codes": "code",
    "projection_templates": "projection_id",
    "promotion_rules": "slot",
    "promotion_slots": "slot",
    "projections": "projection_id",
    "relation_types": "code",
    "role_types": "code",
    "row_types": "code",
    "subcategories": "code",
}
_VOLATILE_RELEASE_FIELDS = frozenset(
    {
        "active_snapshot",
        "created_at",
        "fingerprint",
        "projection_catalog",
        "release_fingerprint",
        "release_path",
        "runtime_semantic_assets",
    }
)


def canonical_locale_list(values: Any) -> list[str]:
    return _canonical_string_list(values, casefold=True)


def canonical_projection_id_list(values: Any) -> list[str]:
    return _canonical_string_list(values, casefold=True)


def build_master_taxonomy_release_id(master_core: dict[str, Any]) -> str:
    return _canonical_sha256(_canonical_json_bytes(normalize_master_core_payload(master_core)))


def legacy_master_taxonomy_release_id(master_taxonomy_id: Any, master_taxonomy_version: Any) -> str:
    master_id = str(master_taxonomy_id or "").strip()
    master_version = str(master_taxonomy_version or "").strip()
    if not master_id or not master_version:
        raise ValueError("master_taxonomy_id und master_taxonomy_version werden fuer die Legacy-Bridge benoetigt.")
    return f"legacy:{master_id}@{master_version}"


def resolve_master_taxonomy_release_id(payload: dict[str, Any]) -> str:
    value = str(payload.get("master_taxonomy_release_id") or "").strip()
    if value:
        return value
    return legacy_master_taxonomy_release_id(
        payload.get("master_taxonomy_id"),
        payload.get("master_taxonomy_version"),
    )


def build_release_fingerprint(payload: dict[str, Any]) -> str:
    return _canonical_sha256(_canonical_json_bytes(normalize_release_fingerprint_payload(payload)))


def normalize_release_fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _json_roundtrip(payload)
    for field_name in _VOLATILE_RELEASE_FIELDS:
        normalized.pop(field_name, None)
    normalized["fingerprint"] = ""
    normalized.pop("created_at", None)
    return _normalize_value(normalized)


def build_projection_catalog_version(payload: dict[str, Any]) -> str:
    normalized = normalize_projection_catalog_payload(payload)
    normalized["catalog_version"] = ""
    return _canonical_sha256(_canonical_json_bytes(normalized))


def normalize_projection_catalog_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _json_roundtrip(payload)
    normalized["catalog_version"] = str(normalized.get("catalog_version") or "")
    return _normalize_value(normalized)


def normalize_master_core_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_value(_json_roundtrip(payload))


def _normalize_value(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_value(child, parent_key=key)
            for key, child in sorted(value.items(), key=lambda item: item[0])
        }
    if isinstance(value, list):
        normalized_items = [_normalize_value(item, parent_key=parent_key) for item in value]
        if _list_is_scalar(normalized_items) and parent_key in _SCALAR_SETLIKE_KEYS:
            return sorted(normalized_items, key=_scalar_sort_key)
        object_sort_key = _OBJECT_LIST_SORT_KEYS.get(parent_key or "")
        if object_sort_key and all(
            isinstance(item, dict) and str(item.get(object_sort_key) or "").strip()
            for item in normalized_items
        ):
            return sorted(
                normalized_items,
                key=lambda item: _scalar_sort_key(str(item.get(object_sort_key) or "").strip()),
            )
        return normalized_items
    return value


def _canonical_string_list(values: Any, *, casefold: bool) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.casefold() if casefold else text
        if key in seen:
            continue
        seen.add(key)
        result.append(text.casefold() if casefold else text)
    return sorted(result, key=_scalar_sort_key)


def _list_is_scalar(values: list[Any]) -> bool:
    return all(not isinstance(item, (dict, list)) for item in values)


def _scalar_sort_key(value: Any) -> tuple[str, str]:
    text = str(value or "").strip()
    return (text.casefold(), text)


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _json_roundtrip(value: Any) -> Any:
    return json.loads(json.dumps(value))
