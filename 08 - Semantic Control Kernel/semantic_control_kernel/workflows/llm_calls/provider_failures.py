from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.llm_retry_policy import LLMRetryPolicy
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.llm_calls import (
    LLMAttemptMetadata,
    LLMCallResult,
    LLMFunctionDefinition,
    LLMProviderResponse,
    LLMValidationReport,
)
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.diagnostics import LLMAttemptDiagnosticSink
from semantic_control_kernel.workflows.llm_calls.final_errors import LLMFinalErrorBuilder


class ProviderFailureHandler:
    def __init__(
        self,
        *,
        artifacts: LLMArtifactStore,
        retry_policy: LLMRetryPolicy,
        diagnostics: LLMAttemptDiagnosticSink,
        final_errors: LLMFinalErrorBuilder,
    ) -> None:
        self.artifacts = artifacts
        self.retry_policy = retry_policy
        self.diagnostics = diagnostics
        self.final_errors = final_errors

    def handle(
        self,
        *,
        definition: LLMFunctionDefinition,
        workflow_run_id: str,
        analysis_run_id: str,
        attempt_index: int,
        max_attempts: int,
        response: LLMProviderResponse,
        prompt_ref: str,
        started_at: str,
        last_snapshot: Mapping[str, Any],
        preserved_state_summary: Mapping[str, Any],
        retry_events: list[dict[str, Any]],
        failed_attempt_refs: list[dict[str, Any]],
        provider_call_count: int,
    ) -> LLMCallResult | None:
        provider_message = (response.error_message or "").strip()
        provider_summary = f"Provider failure: {response.status}."
        if provider_message:
            provider_summary = f"Provider failure: {response.status}: {provider_message}"
        report = LLMValidationReport(
            llm_function_name=definition.llm_function_name,
            attempt_index=attempt_index,
            attempted_schema=definition.output_contract,
            parse_status="missing_output",
            validation_status="failed",
            error_codes=("function_rule_violation",),
            error_summary=provider_summary,
            blocking_paths=("$",),
        )
        response_capture = self.artifacts.build_response_capture(
            definition=definition,
            analysis_run_id=analysis_run_id,
            attempt_index=attempt_index,
            response=response,
            parsed_output={},
            parse_status="missing_output",
            validation_status="failed",
            validation_errors=list(report.error_codes),
        )
        response_ref = self.artifacts.write_attempt_response(
            definition,
            analysis_run_id,
            attempt_index,
            response,
            parsed_output={},
            parse_status="missing_output",
            validation_status="failed",
            validation_errors=list(report.error_codes),
        )
        validation_ref = self.artifacts.write_validation_report(definition, analysis_run_id, attempt_index, report)
        failed_attempt_refs.append(
            {
                "attempt_index": attempt_index,
                "prompt_snapshot_ref": prompt_ref,
                "llm_response_ref": response_ref,
                "validation_report_ref": validation_ref,
            }
        )
        self.diagnostics.record_failed_attempt(
            workflow_run_id=workflow_run_id,
            workflow_tool=definition.llm_function_name,
            analysis_run_id=analysis_run_id,
            llm_function_name=definition.llm_function_name,
            attempt_index=attempt_index,
            max_attempts=max_attempts,
            attempted_schema=definition.output_contract,
            parse_status="missing_output",
            validation_status="failed",
            validation_error_summary=report.error_summary,
            artifact_refs={
                "prompt_snapshot_ref": prompt_ref,
                "raw_response_ref": response_ref,
                "validation_report_ref": validation_ref,
            },
        )
        next_action = self.retry_policy.next_action_for_provider_failure(
            response.status,
            attempt_index,
            provider_message,
        )
        self.artifacts.write_attempt_metadata(
            definition,
            analysis_run_id,
            attempt_index,
            LLMAttemptMetadata(
                analysis_run_id=analysis_run_id,
                llm_function_name=definition.llm_function_name,
                attempt_index=attempt_index,
                max_attempts=max_attempts,
                started_at=started_at,
                ended_at=utc_iso(),
                failure_kind="llm_provider",
                next_action=next_action,
            ),
        )
        if self.retry_policy.should_retry_provider_failure(response.status, attempt_index, provider_message):
            retry_events.append(
                {
                    "event_type": "progress",
                    "status": "retrying",
                    "category": "llm_provider",
                    "llm_function_name": definition.llm_function_name,
                    "attempt_index": attempt_index,
                    "max_attempts": max_attempts,
                }
            )
            return None
        final_error, mirror_event = self.final_errors.provider_failure(
            definition_name=definition.llm_function_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            attempted_schema=definition.output_contract,
            attempts_used=attempt_index,
            provider_status=response.status,
            provider_message=provider_message,
            failed_attempt_refs=tuple(failed_attempt_refs),
            preserved_state_summary=preserved_state_summary,
        )
        self.artifacts.write_final_error(definition, analysis_run_id, final_error)
        self.artifacts.write_flat_attempt_copies(definition, analysis_run_id, last_snapshot, response_capture)
        return LLMCallResult(
            status="failed_provider",
            llm_function_name=definition.llm_function_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            final_error=final_error,
            mirror_event=mirror_event,
            attempts_used=attempt_index,
            retry_events=tuple(retry_events),
            provider_call_count=provider_call_count,
        )
