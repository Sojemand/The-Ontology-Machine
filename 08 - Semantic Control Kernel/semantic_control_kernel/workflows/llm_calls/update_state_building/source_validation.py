from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.llm_validation import LLMValidationContext, validate_structured_output
from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition
from semantic_control_kernel.workflows.llm_calls.update_state_building.errors import UpdateStateBuilderError

def _require_validated_source(function_name: str, proposal: Mapping[str, Any]) -> None:
    definition = get_llm_function_definition(function_name)
    report = validate_structured_output(
        proposal,
        definition=definition,
        context=LLMValidationContext(),
    )
    if not report.passed:
        raise UpdateStateBuilderError(report.error_summary)


def _validate_ref_against_proof(
    proposal_ref: Any,
    proof: Mapping[str, Any],
    *,
    keys: tuple[str, ...],
    label: str,
) -> None:
    if not isinstance(proposal_ref, Mapping):
        raise UpdateStateBuilderError(f"{label} is required.")
    proof_ref = proof.get(label)
    if not isinstance(proof_ref, Mapping):
        proof_ref = proof
    compared = False
    for key in keys:
        if key not in proof_ref:
            continue
        compared = True
        if key not in proposal_ref:
            raise UpdateStateBuilderError(f"{label}.{key} is required.")
        if proposal_ref[key] != proof_ref[key]:
            raise UpdateStateBuilderError(f"{label}.{key} must match real source proof.")
