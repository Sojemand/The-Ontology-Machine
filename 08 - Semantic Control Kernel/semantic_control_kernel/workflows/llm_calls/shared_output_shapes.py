from __future__ import annotations

from typing import Mapping, Sequence

from semantic_control_kernel.policy.promotion_slots import (
    PROMOTION_SLOT_CARDINALITIES,
    PROMOTION_SLOT_QUERY_ROLES,
    PROMOTION_SLOT_SCOPES,
    promotion_value_types,
)
from semantic_control_kernel.workflows.llm_calls.schema_primitives import (
    JsonSchema,
    _array,
    _const,
    _enum,
    _integer,
    _nullable_enum,
    _nullable_integer,
    _nullable_string,
    _number,
    _object,
    _string,
    _string_array,
)


TAXONOMY_TERM_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("domains", ("parent_id?",)),
    ("document_types", ("domains[]", "allowed_categories[]", "allowed_subcategories[]")),
    ("categories", ("domains[]",)),
    ("subcategories", ("parent_category", "domains[]")),
    ("field_codes", ("value_type", "domains[]", "promotion_slot?")),
    ("row_types", ("domains[]", "recommended_cell_codes[]")),
    ("cell_codes", ("value_type", "domains[]")),
)


def projection_schema(allowed_codes: Mapping[str, Sequence[str]]) -> JsonSchema:
    return _object(
        {
            "projection_id": _string(),
            "status": _nullable_enum(("draft", "active")),
            "label": _string(),
            "description": _string(),
            "domain_ids": _code_array("domains", allowed_codes),
            "include_document_types": _code_array("document_types", allowed_codes),
            "include_categories": _code_array("categories", allowed_codes),
            "include_subcategories": _code_array("subcategories", allowed_codes),
            "include_field_codes": _code_array("field_codes", allowed_codes),
            "include_row_types": _code_array("row_types", allowed_codes),
            "include_cell_codes": _code_array("cell_codes", allowed_codes),
            "promotion_rules": _array(_promotion_rule_schema()),
            "routing": _routing_schema(),
            "routing_lexicon": _routing_lexicon_schema(),
        }
    )


def fallback_codes_schema() -> JsonSchema:
    return _object(
        {
            "document_type": _const("other"),
            "category": _const("other"),
            "subcategory": _const("other"),
            "field_code": _const("other"),
            "row_type": _const("other"),
            "cell_code": _const("other"),
        }
    )


def taxonomy_proposal_schema() -> JsonSchema:
    return _object(
        {
            "taxonomy_core": _taxonomy_core_schema(),
            "taxonomy_text": _taxonomy_text_schema(),
            "semantic_binding": _semantic_binding_schema(),
        }
    )


def target_schema(update_state_contract: str) -> JsonSchema:
    return _object({"update_state_contract": _const(update_state_contract)})


def projection_strategy_schema() -> JsonSchema:
    return _object({"mode": _string(), "rationale": _string(), "projection_count": _integer()})


def taxonomy_authoring_ref_schema() -> JsonSchema:
    return _object(
        {
            "source": _enum(("active", "staged", "custom_taxonomy_update_state")),
            "taxonomy_id": _string(),
            "taxonomy_version": _string(),
            "taxonomy_fingerprint": _string(),
        }
    )


def quality_schema() -> JsonSchema:
    return _object({"confidence": _number(), "notes": _string_array()})


def validation_schema() -> JsonSchema:
    return _object({"status": _string(), "open_decisions": _string_array(), "warnings": _string_array()})


def _code_array(section: str, allowed_codes: Mapping[str, Sequence[str]]) -> JsonSchema:
    _ = section, allowed_codes
    return _string_array()


def _promotion_rule_schema() -> JsonSchema:
    return _object({"slot": _string(), "source_paths": _string_array()})


def _routing_schema() -> JsonSchema:
    return _object(
        {
            "when_to_use": _string(),
            "avoid_when": _string(),
            "example_document_types": _string_array(),
            "section_roles": _string_array(),
            "party_roles": _string_array(),
        }
    )


def _domain_marker_entry_schema() -> JsonSchema:
    return _object({"domain_id": _string(), "markers": _string_array()})


def _domain_marker_entries_schema() -> JsonSchema:
    return _array(_domain_marker_entry_schema())


def _routing_lexicon_schema() -> JsonSchema:
    return _object({"text_markers": _string_array(), "domain_markers": _domain_marker_entries_schema()})


def _taxonomy_core_schema() -> JsonSchema:
    properties = {section: _array(_taxonomy_term_schema(fields)) for section, fields in TAXONOMY_TERM_FIELDS}
    properties["promotion_slots"] = _array(_promotion_slot_definition_schema())
    properties["fallback_codes"] = fallback_codes_schema()
    return _object(properties)


def _taxonomy_term_schema(fields: Sequence[str]) -> JsonSchema:
    properties = {"code": _string(), "status": _string()}
    for field in fields:
        name = field.removesuffix("[]").removesuffix("?")
        if field.endswith("[]"):
            properties[name] = _string_array()
        elif field.endswith("?"):
            properties[name] = _nullable_string()
        elif name == "value_type":
            properties[name] = _enum(promotion_value_types())
        else:
            properties[name] = _string()
    return _object(properties)


def _promotion_slot_definition_schema() -> JsonSchema:
    return _object(
        {
            "slot": _string(),
            "label": _nullable_string(),
            "description": _nullable_string(),
            "value_type": _enum(promotion_value_types()),
            "scope": _enum(PROMOTION_SLOT_SCOPES),
            "cardinality": _enum(PROMOTION_SLOT_CARDINALITIES),
            "query_role": _nullable_enum(PROMOTION_SLOT_QUERY_ROLES),
            "display_rank": _nullable_integer(),
        }
    )


def _taxonomy_text_schema() -> JsonSchema:
    term = _object({"code": _string(), "label": _string(), "description": _string(), "aliases": _string_array()})
    return _object({"locale": _string(), "terms": _object({section: _array(term) for section, _fields in TAXONOMY_TERM_FIELDS})})


def _semantic_binding_schema() -> JsonSchema:
    return _object(
        {
            "field_codes": _array(_object({"code": _string(), "promotion_slot": _nullable_string()})),
            "row_types": _array(_object({"code": _string(), "binding_role": _nullable_string()})),
            "cell_codes": _array(_object({"code": _string(), "binding_role": _nullable_string()})),
        }
    )
