from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.llm_adapter import (
    LLMCallCancelled,
    LLMFunctionAdapter,
)
from semantic_control_kernel.policy.llm_retry_policy import LLMRetryPolicy
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.llm_calls import (
    CancellationToken,
    LLMCallResult,
    LLMValidationReport,
)
from semantic_control_kernel.validation.llm_validation import (
    LLMValidationContext,
    derive_validation_context,
)
from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition
from semantic_control_kernel.workflows.llm_calls.provider_attempt import build_provider_request, generate_provider_response
from semantic_control_kernel.workflows.llm_calls.prompts import render_prompt
from semantic_control_kernel.workflows.llm_calls.result_events import cancelled_result, validation_retry_event
from semantic_control_kernel.workflows.llm_calls.runner_services import create_runner_services
from semantic_control_kernel.workflows.llm_calls.runtime import coerce_runtime_settings
from semantic_control_kernel.workflows.llm_calls.validation_finalizer import failed_final_validation_result


class LLMCallRunner:
    def __init__(
        self,
        provider_adapter: LLMFunctionAdapter,
        *,
        artifact_root: str | Path,
        state_root: str | Path | None = None,
        retry_policy: LLMRetryPolicy | None = None,
    ) -> None:
        self.provider_adapter = provider_adapter
        services = create_runner_services(
            artifact_root=artifact_root,
            state_root=state_root,
            retry_policy=retry_policy,
        )
        self.artifacts = services.artifacts
        self.retry_policy = services.retry_policy
        self.state_paths = services.state_paths
        self.diagnostics = services.diagnostics
        self.final_errors = services.final_errors
        self.completed_attempts = services.completed_attempts
        self.provider_failures = services.provider_failures

    def run(
        self,
        llm_function_name: str,
        *,
        workflow_run_id: str,
        analysis_run_id: str,
        input_payload: Any,
        runtime_settings: Mapping[str, Any] | None = None,
        validation_context: LLMValidationContext | None = None,
        preserved_state_summary: Mapping[str, Any] | None = None,
        cancellation: CancellationToken | None = None,
    ) -> LLMCallResult:
        definition = get_llm_function_definition(llm_function_name)
        settings = coerce_runtime_settings(runtime_settings)
        context = validation_context or derive_validation_context(definition, input_payload)
        binding_artifacts = self.artifacts.write_input_artifacts(definition, analysis_run_id, input_payload)
        previous_feedback: str | None = None
        failed_attempt_refs: list[dict[str, Any]] = []
        retry_events: list[dict[str, Any]] = []
        failed_attempt_diagnostic_refs: list[dict[str, Any]] = []
        provider_call_count = 0
        last_report: LLMValidationReport | None = None
        last_response_capture: dict[str, Any] | None = None
        last_snapshot: dict[str, Any] | None = None

        for attempt_index in range(1, self.retry_policy.max_attempts + 1):
            if cancellation is not None and cancellation.is_cancelled:
                return cancelled_result(
                    definition.llm_function_name,
                    workflow_run_id,
                    analysis_run_id,
                    attempts_used=attempt_index - 1,
                    provider_call_count=provider_call_count,
                )
            started_at = utc_iso()
            rendered = render_prompt(
                definition=definition,
                analysis_run_id=analysis_run_id,
                runtime_settings=settings,
                input_payload=input_payload,
                binding_artifacts=binding_artifacts,
                validation_feedback=previous_feedback,
            )
            last_snapshot = rendered.snapshot
            prompt_ref = self.artifacts.write_attempt_snapshot(definition, analysis_run_id, attempt_index, rendered.snapshot)
            request = build_provider_request(
                definition=definition,
                analysis_run_id=analysis_run_id,
                attempt_index=attempt_index,
                settings=settings,
                rendered=rendered,
            )
            try:
                response = generate_provider_response(
                    self.provider_adapter,
                    request,
                    cancellation,
                    settings=settings,
                    attempt_index=attempt_index,
                )
            except LLMCallCancelled:
                return cancelled_result(
                    definition.llm_function_name,
                    workflow_run_id,
                    analysis_run_id,
                    attempts_used=attempt_index - 1,
                    provider_call_count=provider_call_count,
                )
            provider_call_count += 1

            if response.status != "complete":
                provider_result = self.provider_failures.handle(
                    definition=definition,
                    workflow_run_id=workflow_run_id,
                    analysis_run_id=analysis_run_id,
                    attempt_index=attempt_index,
                    max_attempts=self.retry_policy.max_attempts,
                    response=response,
                    prompt_ref=prompt_ref,
                    started_at=started_at,
                    last_snapshot=last_snapshot,
                    preserved_state_summary=preserved_state_summary or {},
                    retry_events=retry_events,
                    failed_attempt_refs=failed_attempt_refs,
                    provider_call_count=provider_call_count,
                )
                if provider_result is not None:
                    return provider_result
                previous_feedback = f"provider_transient_failure: {response.status}"
                continue

            completed_attempt = self.completed_attempts.handle(
                definition=definition,
                workflow_run_id=workflow_run_id,
                analysis_run_id=analysis_run_id,
                attempt_index=attempt_index,
                started_at=started_at,
                response=response,
                rendered_snapshot=rendered.snapshot,
                prompt_ref=prompt_ref,
                context=context,
                retry_events=retry_events,
                provider_call_count=provider_call_count,
            )
            last_report = completed_attempt.report
            last_response_capture = completed_attempt.response_capture
            if completed_attempt.result is not None:
                return completed_attempt.result
            if completed_attempt.failed_attempt_ref is not None:
                failed_attempt_refs.append(completed_attempt.failed_attempt_ref)
            if completed_attempt.diagnostic_ref is not None:
                failed_attempt_diagnostic_refs.append(completed_attempt.diagnostic_ref)
            if self.retry_policy.should_retry_validation_failure(attempt_index):
                retry_events.append(
                    validation_retry_event(
                        definition,
                        workflow_run_id,
                        analysis_run_id,
                        completed_attempt.report,
                        max_attempts=self.retry_policy.max_attempts,
                    )
                )
                previous_feedback = completed_attempt.report.compact_feedback()
                continue
            break

        assert last_report is not None
        assert last_snapshot is not None
        assert last_response_capture is not None
        return failed_final_validation_result(
            artifacts=self.artifacts,
            final_errors=self.final_errors,
            definition=definition,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            attempts_used=self.retry_policy.max_attempts,
            last_report=last_report,
            failed_attempt_refs=failed_attempt_refs,
            failed_attempt_diagnostic_refs=failed_attempt_diagnostic_refs,
            preserved_state_summary=preserved_state_summary,
            retry_events=retry_events,
            provider_call_count=provider_call_count,
            last_snapshot=last_snapshot,
            last_response_capture=last_response_capture,
        )
