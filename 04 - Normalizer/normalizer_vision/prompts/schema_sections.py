"""Shared schema builders for the normalizer prompt contract."""
from __future__ import annotations

from typing import Any

from ..taxonomy import TaxonomyProfile
from .schema_value_types import field_value_schema, promotion_field_specs, value_type_schema


def build_default_model_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "processing", "classification", "context", "content"],
        "properties": {
            "schema_version": {"type": "string"},
            "processing": {
                "type": "object",
                "additionalProperties": False,
                "required": ["model_confidence", "needs_review", "review_reason", "vision_used"],
                "properties": {
                    "model_confidence": {"type": "number"},
                    "needs_review": {"type": "boolean"},
                    "review_reason": {"type": ["string", "null"]},
                    "vision_used": {"type": "boolean"},
                    "processed_at": {"type": "string"},
                    "model": {"type": "string"},
                    "provider": {"type": "string"},
                },
            },
            "classification": _classification_section(),
            "context": {"type": "object", "additionalProperties": True, "properties": _default_context_properties()},
            "content": {
                "type": "object",
                "additionalProperties": False,
                "required": ["structure", "fields", "rows", "free_text"],
                "properties": {
                    "structure": _structure_section(),
                    "fields": {"type": "object", "additionalProperties": True},
                    "rows": {"type": "array", "items": {"type": "object", "additionalProperties": True, "properties": _default_row_properties()}},
                    "free_text": {"type": "string"},
                },
            },
        },
    }


def build_profile_model_output_schema(profile: TaxonomyProfile) -> dict[str, Any]:
    field_codes = list(profile.field_codes.keys())
    cell_codes = list(profile.cell_codes.keys())
    promotion_specs = promotion_field_specs(profile)
    field_properties = {
        code: field_value_schema(
            str(promotion_specs.get(code, {}).get("value_type") or profile.field_codes[code].get("value_type", "string")),
            cardinality=str(promotion_specs.get(code, {}).get("cardinality") or "single"),
            allow_object=code == "other",
        )
        for code in field_codes
    }
    row_properties = {"_row_type": {"type": "string", "enum": list(profile.row_types.keys())}, "_row_index": {"type": "integer"}}
    row_properties.update({code: value_type_schema(str(profile.cell_codes[code].get("value_type", "string")), allow_object=code == "other") for code in cell_codes})
    row_properties["_units"] = _strict_string_map(cell_codes)
    context_properties = _profile_context_properties()
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "processing", "classification", "context", "content"],
        "properties": {
            "schema_version": {"type": "string"},
            "processing": {
                "type": "object",
                "additionalProperties": False,
                "required": ["model_confidence", "needs_review", "review_reason", "vision_used", "processed_at", "model", "provider"],
                "properties": {
                    "model_confidence": {"type": "number"},
                    "needs_review": {"type": "boolean"},
                    "review_reason": {"type": ["string", "null"]},
                    "vision_used": {"type": "boolean"},
                    "processed_at": {"type": ["string", "null"]},
                    "model": {"type": ["string", "null"]},
                    "provider": {"type": ["string", "null"]},
                },
            },
            "classification": _classification_section(list(profile.document_types.keys()), list(profile.categories.keys()), list(profile.subcategories.keys())),
            "context": {"type": "object", "additionalProperties": False, "required": list(context_properties.keys()), "properties": context_properties},
            "content": {
                "type": "object",
                "additionalProperties": False,
                "required": ["structure", "fields", "rows", "free_text"],
                "properties": {
                    "structure": _structure_section(field_codes, cell_codes),
                    "fields": {"type": "object", "additionalProperties": False, "required": list(field_properties.keys()), "properties": field_properties},
                    "rows": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": list(row_properties.keys()), "properties": row_properties}},
                    "free_text": {"type": "string"},
                },
            },
        },
    }


def _classification_section(document_types: list[str] | None = None, categories: list[str] | None = None, subcategories: list[str] | None = None) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "document_type": {"type": "string"},
        "document_type_confidence": {"type": "number"},
        "category": {"type": "string"},
        "subcategory": {"type": "string"},
        "language": {"type": "string"},
        "is_scan": {"type": "boolean"},
        "has_handwriting": {"type": "boolean"},
        "page_count": {"type": "integer"},
    }
    if document_types is not None:
        properties["document_type"]["enum"] = document_types
        properties["category"]["enum"] = categories or []
        properties["subcategory"]["enum"] = subcategories or []
    return {"type": "object", "additionalProperties": False, "required": list(properties.keys()), "properties": properties}


def _structure_section(field_codes: list[str] | None = None, cell_codes: list[str] | None = None) -> dict[str, Any]:
    columns_item: dict[str, Any] = {"type": ["string", "object"]} if cell_codes is None else {"type": "string", "enum": cell_codes}
    field_item: dict[str, Any] = {"type": ["string", "object"]} if field_codes is None else {"type": "string", "enum": field_codes}
    properties = {"type": {"type": "string"}, "columns": {"type": "array", "items": columns_item}, "form_fields": {"type": "array", "items": field_item}}
    if field_codes is not None:
        properties["type"]["enum"] = ["text", "form", "table", "form_with_table", "list", "mixed"]
    return {"type": "object", "additionalProperties": False, "required": list(properties.keys()), "properties": properties}


def _default_context_properties() -> dict[str, Any]:
    return {
        "company": {"type": ["string", "null"]},
        "document_date": {"type": ["string", "null"]},
        "document_title": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "people": {"type": "array", "items": {"type": ["string", "object"]}},
        "organizations": {"type": "array", "items": {"type": ["string", "object"]}},
        "locations": {"type": "array", "items": {"type": ["string", "object"]}},
        "date_range": {"type": "object", "additionalProperties": False, "properties": {"from": {"type": ["string", "null"]}, "to": {"type": ["string", "null"]}}},
        "currencies": {"type": "array", "items": {"type": "string"}},
        "normalization_notes": {"type": "array", "items": {"type": "string"}},
    }


def _profile_context_properties() -> dict[str, Any]:
    properties = _default_context_properties()
    properties["people"] = {"type": "array", "items": {"type": "string"}}
    properties["organizations"] = {"type": "array", "items": {"type": "string"}}
    properties["locations"] = {"type": "array", "items": {"type": "string"}}
    properties["date_range"]["required"] = ["from", "to"]
    properties.update(
        {
            "total_monetary_value": {"type": ["number", "null"]},
            "taxonomy_profile_id": {"type": "string"},
            "recipient_primary": {"type": ["string", "null"]},
            "property_address": {"type": ["string", "null"]},
            "raw_classification": {"type": "object", "additionalProperties": False, "required": ["document_type", "category", "subcategory"], "properties": {"document_type": {"type": ["string", "null"]}, "category": {"type": ["string", "null"]}, "subcategory": {"type": ["string", "null"]}}},
        }
    )
    return properties


def _default_row_properties() -> dict[str, Any]:
    return {"_row_type": {"type": "string"}, "_row_index": {"type": "integer"}, "_units": {"type": "object", "additionalProperties": {"type": "string"}}}


def _strict_string_map(keys: list[str]) -> dict[str, Any]:
    properties = {key: {"type": ["string", "null"]} for key in keys}
    return {"type": ["object", "null"], "additionalProperties": False, "required": list(properties.keys()), "properties": properties}
