from __future__ import annotations

from typing import Any

from semantic_control_kernel.workflows.llm_calls.schema_context import allowed_codes_by_section
from semantic_control_kernel.workflows.llm_calls.schema_primitives import JsonSchema, _array, _const, _object, _string_array
from semantic_control_kernel.workflows.llm_calls.shared_output_shapes import (
    projection_schema,
    projection_strategy_schema,
    quality_schema,
    target_schema,
    taxonomy_authoring_ref_schema,
    taxonomy_proposal_schema,
    validation_schema,
)


def taxonomy_to_sample_schema(input_payload: Any) -> JsonSchema:
    _ = input_payload
    return _object(
        {
            "schema_version": _const("kernel.taxonomy_to_sample_analyses.v1"),
            "source_schema_version": _const("kernel.sample_analyses.v1"),
            "analysis_scope": _const("sample_set"),
            "sample_ids": _string_array(),
            "target": target_schema("kernel.create_taxonomy_update_state.input.v1"),
            "taxonomy_proposal": taxonomy_proposal_schema(),
            "validation": validation_schema(),
            "quality": quality_schema(),
        }
    )

def projections_to_sample_schema(input_payload: Any) -> JsonSchema:
    allowed = allowed_codes_by_section(input_payload)
    return _object(
        {
            "schema_version": _const("kernel.projections_to_sample_analyses.v1"),
            "source_schema_version": _const("kernel.sample_analyses.v1"),
            "taxonomy_view_schema_version": _const("kernel.taxonomy_projection_authoring_view.v1"),
            "analysis_scope": _const("sample_set"),
            "sample_ids": _string_array(),
            "taxonomy_ref": taxonomy_authoring_ref_schema(),
            "target": target_schema("kernel.create_projections_update_state.input.v1"),
            "projection_strategy": projection_strategy_schema(),
            "projection_proposals": _array(projection_schema(allowed)),
            "validation": validation_schema(),
            "quality": quality_schema(),
        }
    )
