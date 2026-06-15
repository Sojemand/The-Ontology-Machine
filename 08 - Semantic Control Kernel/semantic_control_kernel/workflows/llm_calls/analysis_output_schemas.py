from __future__ import annotations

from typing import Any

from semantic_control_kernel.workflows.llm_calls.schema_primitives import (
    JsonSchema,
    _array,
    _const,
    _enum,
    _nullable_string,
    _number,
    _object,
    _string,
    _string_array,
)
from semantic_control_kernel.workflows.llm_calls.shared_output_shapes import (
    fallback_codes_schema,
    projection_schema,
    quality_schema,
)


def sample_analysis_schema(input_payload: Any) -> JsonSchema:
    _ = input_payload
    return _object(
        {
            "schema_version": _const("kernel.sample_analyses.v1"),
            "analysis_scope": _const("sample_set"),
            "input_contract": _const("kernel.analyze_sample.input.v1"),
            "sample_set": _sample_set_schema(),
            "taxonomy_seed": _taxonomy_seed_schema(),
            "projection_seed": _projection_seed_schema(),
            "user_report_samples_seed": _user_report_samples_seed_schema(),
            "quality": quality_schema(),
        }
    )

def _sample_set_schema() -> JsonSchema:
    return _object(
        {
            "sample_ids": _string_array(),
            "summary": _string(),
            "document_family": _string(),
            "shared_semantic_pattern": _string(),
            "meaningful_variations": _string_array(),
            "classification": _object(
                {
                    "domain_codes": _string_array(),
                    "document_type_codes": _string_array(),
                    "category_codes": _string_array(),
                    "subcategory_codes": _string_array(),
                    "confidence": _number(),
                }
            ),
            "structure": _object(
                {
                    "shape": _enum(("text", "form", "table", "form_with_table", "list", "mixed")),
                    "section_roles": _string_array(),
                    "party_roles": _string_array(),
                }
            ),
            "signals": _object(
                {
                    "labels": _string_array(),
                    "text_markers": _string_array(),
                }
            ),
        }
    )


def _taxonomy_seed_schema() -> JsonSchema:
    return _object(
        {
            "candidate_codes": _string_array(),
            "domains": _array(_seed_term_schema()),
            "document_types": _array(_seed_term_schema("domains", "allowed_categories", "allowed_subcategories")),
            "categories": _array(_seed_term_schema("domains")),
            "subcategories": _array(_seed_term_schema("parent_category", "domains")),
            "field_codes": _array(_seed_term_schema("value_type", "domains", "promotion_slot")),
            "row_types": _array(_seed_term_schema("domains", "recommended_cell_codes")),
            "cell_codes": _array(_seed_term_schema("value_type", "domains")),
            "fallback_codes": fallback_codes_schema(),
        }
    )


def _seed_term_schema(*fields: str) -> JsonSchema:
    properties = {"code": _string(), "label": _string(), "description": _string()}
    for field in fields:
        properties[field] = _nullable_string() if field == "promotion_slot" else _string() if field in {"parent_category", "value_type"} else _string_array()
    return _object(properties)


def _projection_seed_schema() -> JsonSchema:
    return _object(
        {
            "candidate_projection_ids": _string_array(),
            "projections": _array(projection_schema({})),
        }
    )


def _user_report_samples_seed_schema() -> JsonSchema:
    return _object(
        {
            "report_purpose": _string(),
            "overview": _string(),
            "taxonomy_view": _object(
                {
                    "domain_findings": _string(),
                    "document_type_findings": _string(),
                    "category_findings": _string(),
                    "field_code_findings": _string(),
                    "row_and_cell_findings": _string(),
                    "taxonomy_gaps_or_decisions": _string_array(),
                }
            ),
            "projection_view": _object(
                {
                    "projection_boundary_findings": _string(),
                    "included_semantics": _string(),
                    "routing_findings": _string(),
                    "promotion_rule_findings": _string(),
                    "split_or_merge_considerations": _string(),
                    "projection_gaps_or_decisions": _string_array(),
                }
            ),
            "sample_set_findings": _object(
                {
                    "what_the_samples_show_together": _string(),
                    "taxonomy_relevance": _string(),
                    "projection_relevance": _string(),
                }
            ),
            "recommended_user_decisions": _string_array(),
            "report_risks_or_uncertainties": _string_array(),
        }
    )
