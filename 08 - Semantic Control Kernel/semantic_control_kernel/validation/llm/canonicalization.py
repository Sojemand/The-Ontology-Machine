"""Top-level canonicalization flow for structured LLM outputs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition
from semantic_control_kernel.validation.llm.common import _STATUS_ALIASES
from semantic_control_kernel.validation.llm.context import LLMValidationContext
from semantic_control_kernel.validation.llm.projection_repair import repair_projection_proposal
from semantic_control_kernel.validation.llm.schema_softening import soften_to_schema
from semantic_control_kernel.validation.llm.seed_repair import repair_sample_analysis_seed
from semantic_control_kernel.workflows.llm_calls.output_schemas import build_output_schema


_TOLERANT_SCHEMA_FUNCTIONS = {
    "analyze_samples",
    "create_projections_to_sample_analyses",
}


def canonicalize_structured_output(
    payload: Mapping[str, Any],
    *,
    definition: LLMFunctionDefinition,
    context: LLMValidationContext,
) -> dict[str, Any]:
    copied = deepcopy(dict(payload))
    _normalize_status_aliases(copied)
    if definition.llm_function_name in _TOLERANT_SCHEMA_FUNCTIONS:
        target_schema = build_output_schema(definition, context.input_payload)
        if target_schema is not None:
            copied = soften_to_schema(copied, target_schema)
    if definition.llm_function_name == "analyze_samples":
        repair_sample_analysis_seed(copied, context)
    elif definition.llm_function_name == "create_projections_to_sample_analyses":
        repair_projection_proposal(copied)
    return copied


def _normalize_status_aliases(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key in {"status", "target_status"} and isinstance(child, str):
                value[key] = _STATUS_ALIASES.get(child.strip().lower(), child)
            else:
                _normalize_status_aliases(child)
    elif isinstance(value, list):
        for item in value:
            _normalize_status_aliases(item)


__all__ = ["canonicalize_structured_output"]
