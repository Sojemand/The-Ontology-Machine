"""Allowed key sets for source package validation."""
from __future__ import annotations

from . import policy

MASTER_CORE_KEYS = (
    "taxonomy_id", "taxonomy_version", "status", "defaults", "governance",
    "compatibility", "promotion_slots", "domains", "document_types",
    "categories", "subcategories", "field_codes", "row_types", "cell_codes",
    "entity_types", "role_types", "relation_types",
)
MASTER_TEXT_KEYS = ("description", *policy.MASTER_TEXT_COLLECTIONS)
PROJECTION_CORE_KEYS = (
    "projection_id", "projection_family", "materialization_profile_id",
    "extends", "domain_ids", "include_document_types", "include_categories",
    "include_subcategories", "include_field_codes", "include_row_types",
    "include_cell_codes", "promotion_rules", "compatibility", "routing",
)
PROJECTION_TEXT_KEYS = ("label", "description", "routing", "routing_lexicon")
