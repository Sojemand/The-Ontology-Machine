from __future__ import annotations

from typing import Any

from semantic_control_kernel.types.llm_calls import LLMCallResult, LLMFinalError, LLMValidationReport


def cancelled_result(
    function_name: str,
    workflow_run_id: str,
    analysis_run_id: str,
    *,
    attempts_used: int,
    provider_call_count: int,
) -> LLMCallResult:
    return LLMCallResult(
        status="cancelled",
        llm_function_name=function_name,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        attempts_used=attempts_used,
        provider_call_count=provider_call_count,
        mirror_event={
            "event_type": "workflow_cancelled",
            "severity": "info",
            "is_kernel_auto_call": True,
            "llm_function_name": function_name,
            "workflow_run_id": workflow_run_id,
            "analysis_run_id": analysis_run_id,
        },
    )


def validation_retry_event(
    definition,
    workflow_run_id: str,
    analysis_run_id: str,
    report: LLMValidationReport,
    *,
    max_attempts: int,
) -> dict[str, Any]:
    return {
        "event_type": "llm_validation_retry",
        "severity": "info",
        "is_kernel_auto_call": True,
        "llm_function_name": definition.llm_function_name,
        "workflow_run_id": workflow_run_id,
        "analysis_run_id": analysis_run_id,
        "attempt_index": report.attempt_index,
        "max_attempts": max_attempts,
        "attempted_schema": definition.output_contract,
        "validation_error_summary": report.error_summary,
        "next_kernel_action": "retry_same_isolated_task_with_compact_validation_feedback",
    }


def final_mirror_event(final_error: LLMFinalError, event_type: str, severity: str) -> dict[str, Any]:
    payload = final_error.to_dict()
    return {
        "event_type": event_type,
        "severity": severity,
        "is_kernel_auto_call": True,
        "llm_function_name": payload["llm_function_name"],
        "workflow_run_id": payload["workflow_run_id"],
        "analysis_run_id": payload["analysis_run_id"],
        "attempted_schema": payload["attempted_schema"],
        "attempts_used": payload["attempts_used"],
        "validation_error_summary": payload["validation_error_summary"],
        "failed_attempt_artifact_refs": payload["failed_attempt_artifact_refs"],
        "preserved_state_summary": payload["preserved_state_summary"],
        "recovery_options": payload["recovery_options"],
        "allowed_agent_tools": payload["allowed_agent_tools"],
        "support_bundle_ref": payload["support_bundle_ref"],
    }
