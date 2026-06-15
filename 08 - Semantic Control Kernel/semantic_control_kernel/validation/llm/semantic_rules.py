from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.llm.analysis_rules import (
    projection_proposal_errors,
    sample_analysis_errors,
    taxonomy_proposal_errors,
)
from semantic_control_kernel.validation.llm.common import ValidationError, ref_mismatch_errors
from semantic_control_kernel.validation.llm.context import LLMValidationContext


def context_mismatch_errors(payload: Mapping[str, Any], context: LLMValidationContext) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if context.expected_sample_ids and "sample_ids" in payload:
        actual = tuple(str(item) for item in payload.get("sample_ids", ()))
        if actual != context.expected_sample_ids:
            errors.append(
                (
                    "sample_id_mismatch",
                    f"sample_ids must match prompt input order {context.expected_sample_ids}.",
                    "$.sample_ids",
                )
            )
    if context.expected_database_ref and isinstance(payload.get("database_ref"), Mapping):
        errors.extend(
            ref_mismatch_errors(
                actual=payload["database_ref"],
                expected=context.expected_database_ref,
                keys=("database_id", "database_fingerprint"),
                code="database_reference_mismatch",
                path="$.database_ref",
            )
        )
    if context.expected_taxonomy_ref and isinstance(payload.get("taxonomy_ref"), Mapping):
        errors.extend(
            ref_mismatch_errors(
                actual=payload["taxonomy_ref"],
                expected=context.expected_taxonomy_ref,
                keys=("source", "taxonomy_id", "taxonomy_version", "taxonomy_fingerprint"),
                code="taxonomy_fingerprint_mismatch",
                path="$.taxonomy_ref",
            )
        )
    if context.expected_semantic_release_ref and isinstance(payload.get("semantic_release_ref"), Mapping):
        errors.extend(
            ref_mismatch_errors(
                actual=payload["semantic_release_ref"],
                expected=context.expected_semantic_release_ref,
                keys=("release_id", "release_version", "release_fingerprint"),
                code="projection_fingerprint_mismatch",
                path="$.semantic_release_ref",
            )
        )
    return errors


def function_specific_errors(
    function_name: str,
    payload: Mapping[str, Any],
    context: LLMValidationContext,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if function_name == "analyze_samples":
        errors.extend(sample_analysis_errors(payload, context))
    elif function_name == "create_taxonomy_to_sample_analyses":
        errors.extend(taxonomy_proposal_errors(payload))
    elif function_name == "create_projections_to_sample_analyses":
        errors.extend(projection_proposal_errors(payload, context))
    errors.extend(confidence_bound_errors(payload))
    return errors


def confidence_bound_errors(value: Any, path: str = "$") -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).endswith("confidence") or str(key) == "confidence":
                if isinstance(child, (int, float)) and not 0 <= float(child) <= 1:
                    errors.append(("function_rule_violation", "confidence values must be between 0 and 1.", child_path))
            errors.extend(confidence_bound_errors(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(confidence_bound_errors(child, f"{path}[{index}]"))
    return errors
