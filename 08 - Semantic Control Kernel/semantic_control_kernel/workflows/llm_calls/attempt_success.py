from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.llm_retry_policy import LLMRetryPolicy
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.llm_calls import LLMAttemptMetadata, LLMCallResult, LLMFunctionDefinition
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore


def build_success_result(
    *,
    artifacts: LLMArtifactStore,
    retry_policy: LLMRetryPolicy,
    definition: LLMFunctionDefinition,
    workflow_run_id: str,
    analysis_run_id: str,
    attempt_index: int,
    started_at: str,
    output_for_success: Any,
    rendered_snapshot: Mapping[str, Any],
    response_capture: Mapping[str, Any],
    retry_events: list[dict[str, Any]],
    provider_call_count: int,
) -> LLMCallResult:
    output_ref = artifacts.write_canonical_output(definition, analysis_run_id, output_for_success)
    artifacts.write_attempt_metadata(
        definition,
        analysis_run_id,
        attempt_index,
        LLMAttemptMetadata(
            analysis_run_id=analysis_run_id,
            llm_function_name=definition.llm_function_name,
            attempt_index=attempt_index,
            max_attempts=retry_policy.max_attempts,
            started_at=started_at,
            ended_at=utc_iso(),
            failure_kind=None,
            next_action="consume_validated_output",
        ),
    )
    artifacts.write_flat_attempt_copies(definition, analysis_run_id, rendered_snapshot, response_capture)
    return LLMCallResult(
        status="succeeded",
        llm_function_name=definition.llm_function_name,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        output_artifact_ref={
            "artifact_path": output_ref,
            "schema_version": definition.output_contract,
        },
        output=output_for_success,
        attempts_used=attempt_index,
        retry_events=tuple(retry_events),
        provider_call_count=provider_call_count,
    )
