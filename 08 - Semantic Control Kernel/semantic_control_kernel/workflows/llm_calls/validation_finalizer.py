from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.llm_calls import LLMCallResult, LLMValidationReport


def failed_final_validation_result(
    *,
    artifacts: Any,
    final_errors: Any,
    definition: Any,
    workflow_run_id: str,
    analysis_run_id: str,
    attempts_used: int,
    last_report: LLMValidationReport,
    failed_attempt_refs: list[dict[str, Any]],
    failed_attempt_diagnostic_refs: list[dict[str, Any]],
    preserved_state_summary: Mapping[str, Any] | None,
    retry_events: list[dict[str, Any]],
    provider_call_count: int,
    last_snapshot: dict[str, Any],
    last_response_capture: dict[str, Any],
) -> LLMCallResult:
    final_error, mirror_event = final_errors.validation_failure(
        definition_name=definition.llm_function_name,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        attempted_schema=definition.output_contract,
        attempts_used=attempts_used,
        validation_error_summary=last_report.error_summary,
        failed_attempt_refs=tuple(failed_attempt_refs),
        failed_attempt_diagnostic_refs=tuple(failed_attempt_diagnostic_refs),
        preserved_state_summary=preserved_state_summary or {},
    )
    artifacts.write_final_error(definition, analysis_run_id, final_error)
    artifacts.write_flat_attempt_copies(definition, analysis_run_id, last_snapshot, last_response_capture)
    return LLMCallResult(
        status="failed_final_validation",
        llm_function_name=definition.llm_function_name,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        final_error=final_error,
        mirror_event=mirror_event,
        attempts_used=attempts_used,
        retry_events=tuple(retry_events),
        provider_call_count=provider_call_count,
    )
