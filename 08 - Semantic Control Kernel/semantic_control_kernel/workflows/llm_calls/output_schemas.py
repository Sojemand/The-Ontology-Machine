from __future__ import annotations

from collections.abc import Callable
from typing import Any

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition
from semantic_control_kernel.workflows.llm_calls.analysis_output_schemas import sample_analysis_schema
from semantic_control_kernel.workflows.llm_calls.schema_primitives import JsonSchema, schema_supports_strict
from semantic_control_kernel.workflows.llm_calls.taxonomy_projection_output_schemas import (
    projections_to_sample_schema,
    taxonomy_to_sample_schema,
)


OutputSchemaBuilder = Callable[[Any], JsonSchema]


def output_schema_name(definition: LLMFunctionDefinition) -> str:
    name = f"kernel_{definition.llm_function_name}_output"
    return "".join(char if char.isalnum() or char in "_-" else "_" for char in name)[:64]


def build_output_schema(definition: LLMFunctionDefinition, input_payload: Any) -> JsonSchema | None:
    if definition.call_type == "report_text":
        return None
    builder = _SCHEMA_BUILDERS.get(definition.llm_function_name)
    if builder is None:
        return None
    return builder(input_payload)


_SCHEMA_BUILDERS: dict[str, OutputSchemaBuilder] = {
    "analyze_samples": sample_analysis_schema,
    "create_taxonomy_to_sample_analyses": taxonomy_to_sample_schema,
    "create_projections_to_sample_analyses": projections_to_sample_schema,
}


__all__ = [
    "JsonSchema",
    "build_output_schema",
    "output_schema_name",
    "schema_supports_strict",
]
