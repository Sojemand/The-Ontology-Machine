from __future__ import annotations

from dataclasses import dataclass
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
from semantic_control_kernel.validation.llm_validation import LLMValidationContext, validate_structured_output_text
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.attempt_success import build_success_result
from semantic_control_kernel.workflows.llm_calls.diagnostics import LLMAttemptDiagnosticSink
from semantic_control_kernel.workflows.llm_calls.function_registry import REPORT_TEXT
from semantic_control_kernel.workflows.llm_calls.report_validation import normalize_report_output, validate_report_output


@dataclass(frozen=True)
class CompletedAttemptResult:
    result: LLMCallResult | None
    report: LLMValidationReport
    response_capture: dict[str, Any]
    failed_attempt_ref: dict[str, Any] | None = None
    diagnostic_ref: dict[str, Any] | None = None


class CompletedAttemptHandler:
    def __init__(
        self,
        *,
        artifacts: LLMArtifactStore,
        retry_policy: LLMRetryPolicy,
        diagnostics: LLMAttemptDiagnosticSink,
    ) -> None:
        self.artifacts = artifacts
        self.retry_policy = retry_policy
        self.diagnostics = diagnostics

    def handle(
        self,
        *,
        definition: LLMFunctionDefinition,
        workflow_run_id: str,
        analysis_run_id: str,
        attempt_index: int,
        started_at: str,
        response: LLMProviderResponse,
        rendered_snapshot: Mapping[str, Any],
        prompt_ref: str,
        context: LLMValidationContext,
        retry_events: list[dict[str, Any]],
        provider_call_count: int,
    ) -> CompletedAttemptResult:
        parsed_output: Any = {}
        if definition.call_type == REPORT_TEXT:
            report_text = normalize_report_output(response.output_text)
            report = validate_report_output(
                report_text=report_text,
                definition=definition,
                attempt_index=attempt_index,
            )
            output_for_success: Any = report_text
            parse_status = report.parse_status
        else:
            parsed_output, report = validate_structured_output_text(
                output_text=response.output_text,
                definition=definition,
                context=context,
                attempt_index=attempt_index,
            )
            output_for_success = parsed_output
            parse_status = report.parse_status
            if parsed_output is not None:
                self.artifacts.write_parsed_output(definition, analysis_run_id, attempt_index, parsed_output)

        validation_errors = list(report.error_codes)
        response_capture = self.artifacts.build_response_capture(
            definition=definition,
            analysis_run_id=analysis_run_id,
            attempt_index=attempt_index,
            response=response,
            parsed_output=parsed_output,
            parse_status=parse_status,
            validation_status=report.validation_status,
            validation_errors=validation_errors,
        )
        response_ref = self.artifacts.write_attempt_response(
            definition,
            analysis_run_id,
            attempt_index,
            response,
            parsed_output=parsed_output,
            parse_status=parse_status,
            validation_status=report.validation_status,
            validation_errors=validation_errors,
        )
        validation_ref = self.artifacts.write_validation_report(definition, analysis_run_id, attempt_index, report)
        if report.passed:
            return CompletedAttemptResult(
                result=build_success_result(
                    artifacts=self.artifacts,
                    retry_policy=self.retry_policy,
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    analysis_run_id=analysis_run_id,
                    attempt_index=attempt_index,
                    started_at=started_at,
                    output_for_success=output_for_success,
                    rendered_snapshot=rendered_snapshot,
                    response_capture=response_capture,
                    retry_events=retry_events,
                    provider_call_count=provider_call_count,
                ),
                report=report,
                response_capture=response_capture,
            )

        failed_attempt_ref = {
            "attempt_index": attempt_index,
            "prompt_snapshot_ref": prompt_ref,
            "llm_response_ref": response_ref,
            "validation_report_ref": validation_ref,
        }
        diagnostic_ref = self.diagnostics.record_failed_attempt(
            workflow_run_id=workflow_run_id,
            workflow_tool=definition.llm_function_name,
            analysis_run_id=analysis_run_id,
            llm_function_name=definition.llm_function_name,
            attempt_index=attempt_index,
            max_attempts=self.retry_policy.max_attempts,
            attempted_schema=definition.output_contract,
            parse_status=parse_status,
            validation_status=report.validation_status,
            validation_error_summary=report.error_summary,
            artifact_refs={
                "prompt_snapshot_ref": prompt_ref,
                "raw_response_ref": response_ref,
                "validation_report_ref": validation_ref,
            },
        )
        self.artifacts.write_attempt_metadata(
            definition,
            analysis_run_id,
            attempt_index,
            LLMAttemptMetadata(
                analysis_run_id=analysis_run_id,
                llm_function_name=definition.llm_function_name,
                attempt_index=attempt_index,
                max_attempts=self.retry_policy.max_attempts,
                started_at=started_at,
                ended_at=utc_iso(),
                failure_kind="llm_validation",
                next_action=self.retry_policy.next_action_for_validation(attempt_index),
            ),
        )
        return CompletedAttemptResult(
            result=None,
            report=report,
            response_capture=response_capture,
            failed_attempt_ref=failed_attempt_ref,
            diagnostic_ref=diagnostic_ref,
        )
