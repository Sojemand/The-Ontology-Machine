from __future__ import annotations

import json
from typing import Any

from ..taxonomy import TaxonomyProfile
from .promotion_contract import promotion_field_specs
from .types import MODEL_OUTPUT_TEMPLATE


def build_dynamic_output_contract(profile: TaxonomyProfile) -> str:
    example = {
        "schema_version": MODEL_OUTPUT_TEMPLATE["schema_version"],
        "processing": {
            "model_confidence": 0.0,
            "needs_review": False,
            "review_reason": None,
            "vision_used": False,
            "processed_at": "2026-03-23T10:15:00Z",
            "model": "gpt-5.4-mini",
            "provider": "openai",
        },
        "classification": {
            "document_type": first_code(profile.document_types),
            "document_type_confidence": 0.0,
            "category": first_code(profile.categories),
            "subcategory": first_code(profile.subcategories),
            "language": "und",
            "is_scan": False,
            "has_handwriting": False,
            "page_count": 1,
        },
        "context": {
            "company": None,
            "document_date": None,
            "document_title": None,
            "description": "Compact evidence-bound English semantic summary.",
            "tags": [],
            "people": [],
            "organizations": [],
            "locations": [],
            "date_range": {"from": None, "to": None},
            "currencies": [],
            "total_monetary_value": None,
            "taxonomy_profile_id": profile.projection_id,
            "raw_classification": {"document_type": None, "category": None, "subcategory": None},
            "normalization_notes": [],
            "recipient_primary": None,
            "property_address": None,
        },
        "content": {
            "structure": {
                "type": "text|form|table|form_with_table|list|mixed",
                "columns": example_codes(profile.cell_codes),
                "form_fields": example_codes(profile.field_codes),
            },
            "fields": example_fields(profile),
            "rows": [example_row(profile)],
            "free_text": "compact retrieval text from canonical codes and values",
        },
    }
    return json.dumps(example, indent=2, ensure_ascii=False)


def example_fields(profile: TaxonomyProfile) -> dict[str, Any]:
    promotion_specs = promotion_field_specs(profile)
    fields: dict[str, Any] = {}
    for code in promotion_specs:
        if code not in profile.field_codes:
            continue
        fields[code] = ["value one", "value two"] if promotion_specs[code]["cardinality"] == "multi" else "value"
    if fields:
        return fields
    for code in example_codes(profile.field_codes):
        fields[code] = None if code == "other" else "value"
    return fields


def example_row(profile: TaxonomyProfile) -> dict[str, Any]:
    row = {"_row_type": first_code(profile.row_types), "_row_index": 0}
    for code in example_codes(profile.cell_codes):
        row[code] = "compact row value"
    return row


def example_codes(items: dict[str, dict[str, Any]]) -> list[str]:
    preferred = [code for code in items if code != "other"]
    if preferred:
        return preferred[:4]
    return list(items)[:1]


def first_code(items: dict[str, dict[str, Any]]) -> str:
    return next(iter(items), "other")
