"""Projection payload builders for minimal custom releases."""
from __future__ import annotations

from typing import Any

from ..taxonomy.types import DEFAULT_MATERIALIZATION_PROFILE_ID
from .minimal_custom_values import dedupe
from .promotion_rules import promotion_rules_from_fields

DEFAULT_SECTION_ROLES = ["header", "summary", "body", "details", "timeline", "participants", "other"]


def projection_core(
    *,
    projection_id: str,
    domain_id: str,
    document_type_ids: list[str],
    category_id: str,
    subcategory_id: str,
    fields: list[dict[str, Any]],
    field_ids: list[str],
    row_ids: list[str],
    cell_ids: list[str],
) -> dict[str, Any]:
    return {
        "projection_id": projection_id,
        "projection_family": "custom",
        "materialization_profile_id": DEFAULT_MATERIALIZATION_PROFILE_ID,
        "extends": [],
        "domain_ids": [domain_id],
        "include_document_types": dedupe([*document_type_ids, "other"]),
        "include_categories": dedupe([category_id, "other"]),
        "include_subcategories": dedupe([subcategory_id, "other"]),
        "include_field_codes": dedupe([*field_ids, "other"]),
        "include_row_types": dedupe([*row_ids, "other"]),
        "include_cell_codes": dedupe([*cell_ids, "other"]),
        "promotion_rules": promotion_rules_from_fields(fields, include_field_codes=dedupe([*field_ids, "other"])),
        "compatibility": {},
        "routing": {
            "example_document_types": list(document_type_ids),
            "section_roles": list(DEFAULT_SECTION_ROLES),
            "party_roles": ["other"],
        },
    }
