"""Master payload builders for minimal custom releases."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .minimal_custom_values import dedupe, other_text, text_entry
from .promotion_rules import promotion_slots_from_fields

DEFAULT_RELATION_TYPES = {
    "normalized_from": {"label": "Normalized from"},
    "document_has_entity": {"label": "Document has entity"},
    "entity_reference": {"label": "Entity reference"},
}


def master_core(
    *,
    release_version: str,
    domain_id: str,
    category_id: str,
    subcategory_id: str,
    document_types: list[str],
    fields: list[dict[str, Any]],
    row_types: list[str],
    cell_codes: list[dict[str, Any]],
) -> dict[str, Any]:
    all_document_types = dedupe([*document_types, "other"])
    all_rows = dedupe([*row_types, "other"])
    all_cells = dedupe([*[item["code"] for item in cell_codes], "other"])
    return {
        "taxonomy_id": "normalizer_taxonomy.custom",
        "taxonomy_version": release_version,
        "status": "draft",
        "defaults": {
            "fallback_document_type": "other",
            "fallback_category": "other",
            "fallback_subcategory": "other",
            "fallback_field_code": "other",
            "fallback_row_type": "other",
            "fallback_cell_code": "other",
        },
        "governance": {
            "code_policy": {"format": "snake_case", "character_set": "ascii", "rename_strategy": "forbidden", "deprecation_strategy": "mark_only"},
            "review_rules": {"require_description": True, "require_domain_assignment": True, "require_fallback_code": True},
        },
        "compatibility": {"taxonomy_contract": "semantic_release_v1", "backward_compatible_with": ["1.0"], "notes": ["Minimal custom taxonomy generated for one special-purpose archive."]},
        "promotion_slots": promotion_slots_from_fields(fields),
        "domains": {domain_id: {"parent_id": None, "status": "active"}, "other": {"parent_id": None, "status": "active"}},
        "document_types": _document_type_core(all_document_types, domain_id=domain_id, category_id=category_id, subcategory_id=subcategory_id),
        "categories": {category_id: {"status": "active", "domains": [domain_id]}, "other": {"status": "active", "domains": ["other"]}},
        "subcategories": {subcategory_id: {"status": "active", "parent_category": category_id, "domains": [domain_id]}, "other": {"status": "active", "parent_category": "other", "domains": ["other"]}},
        "field_codes": {**{item["code"]: field_core(item, domain_id=domain_id) for item in fields}, "other": field_core({"code": "other", "value_type": "string"}, domain_id="other")},
        "row_types": {**{item_id: row_core(item_id, domain_id=domain_id, cell_codes=all_cells) for item_id in all_rows if item_id != "other"}, "other": row_core("other", domain_id="other", cell_codes=["other"], materialize_each_row=False)},
        "cell_codes": {**{item["code"]: cell_core(item, domain_id=domain_id) for item in cell_codes}, "other": cell_core({"code": "other", "value_type": "string"}, domain_id="other")},
        "entity_types": {"document_fact": {}, "event": {}, "party": {}},
        "role_types": {**{item_id: {} for item_id in all_rows}, "other": {}},
        "relation_types": {key: {} for key in DEFAULT_RELATION_TYPES},
    }


def master_text(
    *,
    archive_description: str,
    domain: dict[str, Any],
    category: dict[str, Any],
    subcategory: dict[str, Any],
    document_types: list[dict[str, Any]],
    field_codes: list[dict[str, Any]],
    row_types: list[dict[str, Any]],
    cell_codes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "description": archive_description,
        "domains": {domain["code"]: text_entry(domain), "other": other_text("Fallback domain.")},
        "document_types": {**{item["code"]: text_entry(item) for item in document_types}, "other": other_text("Fallback document type for unclear cases.")},
        "categories": {category["code"]: text_entry(category), "other": other_text("Fallback category.")},
        "subcategories": {subcategory["code"]: text_entry(subcategory), "other": other_text("Fallback subcategory.")},
        "field_codes": {**{item["code"]: text_entry(item) for item in field_codes}, "other": other_text("Fallback field.")},
        "row_types": {**{item["code"]: text_entry(item) for item in row_types}, "other": other_text("Fallback row type.")},
        "cell_codes": {**{item["code"]: text_entry(item) for item in cell_codes}, "other": other_text("Fallback cell value.")},
        "entity_types": {
            "document_fact": {"label": "Document fact", "description": "General fact from the document."},
            "event": {"label": "Event", "description": "Event, scene or point in time."},
            "party": {"label": "Party", "description": "Person or group in the document."},
        },
        "role_types": {**{item["code"]: {"label": item["label"]} for item in row_types}, "other": {"label": "Other"}},
        "relation_types": deepcopy(DEFAULT_RELATION_TYPES),
    }


def field_core(item: dict[str, Any], *, domain_id: str) -> dict[str, Any]:
    code = item["code"]
    binding = dict(item.get("semantic_binding") or {})
    binding.setdefault("entity_type", "document_fact")
    binding.setdefault("attribute_code", code)
    return {"status": "active", "value_type": item.get("value_type") or "string", "domains": [domain_id], "semantic_binding": binding}


def row_core(item_id: str, *, domain_id: str, cell_codes: list[str], materialize_each_row: bool = True) -> dict[str, Any]:
    return {"status": "active", "domains": [domain_id], "recommended_cell_codes": list(cell_codes), "semantic_binding": {"entity_type": "document_fact", "role_type": item_id, "materialize_each_row": materialize_each_row}}


def cell_core(item: dict[str, Any], *, domain_id: str) -> dict[str, Any]:
    return {"status": "active", "value_type": item.get("value_type") or "string", "domains": [domain_id], "semantic_binding": {"attribute_code": item["code"], "materialize_on_row_entity": True}}


def _document_type_core(all_document_types: list[str], *, domain_id: str, category_id: str, subcategory_id: str) -> dict[str, Any]:
    return {
        **{
            item_id: {"status": "active", "domains": [domain_id], "allowed_categories": [category_id, "other"], "allowed_subcategories": [subcategory_id, "other"]}
            for item_id in all_document_types
            if item_id != "other"
        },
        "other": {"status": "active", "domains": ["other"], "allowed_categories": ["other"], "allowed_subcategories": ["other"]},
    }
