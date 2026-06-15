from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.types.llm_calls import LLMCallResult
from semantic_control_kernel.workflows.database_creation.shared_steps import create_blocker
from semantic_control_kernel.workflows.llm_calls.user_reports import report_request_for_analysis


@dataclass(frozen=True)
class AnalysisReportOutcome:
    report_function: str
    report_text: str = ""
    unavailable_detail: Mapping[str, Any] | None = None

    @property
    def available(self) -> bool:
        return bool(self.report_text.strip())


def run_analysis_report(
    run_llm: Any,
    llm_port: Any,
    analysis_function_name: str,
    *,
    workflow_run_id: str,
    analysis_run_id: str,
    artifact_root: str | Path,
    analysis_output: Any,
    runtime_settings: Mapping[str, Any] | None,
) -> AnalysisReportOutcome | None:
    request = report_request_for_analysis(analysis_function_name, analysis_output)
    if request is None:
        return None
    report_function, report_input = request
    result = run_llm(
        llm_port,
        report_function,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        artifact_root=artifact_root,
        input_payload=report_input,
        runtime_settings=runtime_settings,
        progress_failure_mode="optional_unavailable",
    )
    if getattr(result, "succeeded", False) and isinstance(result.output, str) and result.output.strip():
        return AnalysisReportOutcome(report_function=report_function, report_text=result.output.strip())
    detail: dict[str, Any] = {
        "status": str(getattr(result, "status", "") or "unknown"),
        "attempts_used": int(getattr(result, "attempts_used", 0) or 0),
    }
    final_error = getattr(result, "final_error", None)
    if final_error is not None:
        detail["validation_error_summary"] = str(getattr(final_error, "validation_error_summary", "") or "")
    return AnalysisReportOutcome(report_function=report_function, unavailable_detail=detail)


def blocker_from_llm_result(step_id: str, result: LLMCallResult) -> DatabaseCreationBlocker | None:
    if result.succeeded:
        return None
    summary = f"LLM function {result.llm_function_name} did not return a validated output."
    diagnostics = ()
    if result.final_error is not None:
        summary = result.final_error.validation_error_summary or summary
        diagnostics = (result.final_error.to_dict(),)
    if result.status == "failed_final_validation":
        return create_blocker(
            step_id=step_id,
            function_or_route=result.llm_function_name,
            blocker_code="final_llm_validation_failure",
            recovery_state_class="final_llm_validation_failure",
            summary=summary,
            diagnostics=diagnostics,
        )
    return create_blocker(
        step_id=step_id,
        function_or_route=result.llm_function_name,
        blocker_code="pipeline_capability_missing",
        recovery_state_class="support_only_unrecoverable",
        summary=summary,
        diagnostics=diagnostics,
    )
