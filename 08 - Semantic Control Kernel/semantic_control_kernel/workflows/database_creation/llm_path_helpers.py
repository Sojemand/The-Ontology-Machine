from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from semantic_control_kernel.adapters.llm_adapter import LLMAdapterError
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.types.llm_calls import LLMCallResult
from semantic_control_kernel.workflows.database_creation.shared_steps import build_analyze_sample_inputs, create_blocker
from semantic_control_kernel.workflows.database_creation.llm_path_reports import (
    AnalysisReportOutcome,
    blocker_from_llm_result,
    run_analysis_report as _run_analysis_report,
)
from semantic_control_kernel.workflows.llm_calls.update_state_builders import UpdateStateBuilderError


def analysis_id(workflow_run_id: str, suffix: str) -> str:
    return f"{workflow_run_id}_{suffix}"


def run_llm(
    llm_port: Any,
    function_name: str,
    *,
    workflow_run_id: str,
    analysis_run_id: str,
    artifact_root: str | Path,
    input_payload: Any,
    runtime_settings: Mapping[str, Any] | None,
    progress_failure_mode: str | None = None,
) -> LLMCallResult:
    if hasattr(llm_port, "run"):
        call_kwargs = {
            "workflow_run_id": workflow_run_id,
            "analysis_run_id": analysis_run_id,
            "input_payload": input_payload,
            "runtime_settings": runtime_settings,
            "preserved_state_summary": {"resumable_state": True, "cancellable": True},
            "artifact_root": artifact_root,
        }
        if progress_failure_mode is not None:
            call_kwargs["progress_failure_mode"] = progress_failure_mode
        try:
            return llm_port.run(function_name, **call_kwargs)
        except TypeError:
            fallback_kwargs = dict(call_kwargs)
            fallback_kwargs.pop("artifact_root", None)
            fallback_kwargs.pop("progress_failure_mode", None)
            return llm_port.run(function_name, **fallback_kwargs)
    method = getattr(llm_port, function_name)
    return method(
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        artifact_root=artifact_root,
        input_payload=input_payload,
    )


def run_analysis_report(
    llm_port: Any,
    analysis_function_name: str,
    *,
    workflow_run_id: str,
    analysis_run_id: str,
    artifact_root: str | Path,
    analysis_output: Any,
    runtime_settings: Mapping[str, Any] | None,
) -> AnalysisReportOutcome | None:
    return _run_analysis_report(
        run_llm,
        llm_port,
        analysis_function_name,
        workflow_run_id=workflow_run_id,
        analysis_run_id=analysis_run_id,
        artifact_root=artifact_root,
        analysis_output=analysis_output,
        runtime_settings=runtime_settings,
    )


def run_sample_proposal_update_path(
    llm_port: Any,
    *,
    unavailable_step_id: str,
    unavailable_summary: str,
    workflow_run_id: str,
    analysis_suffix: str,
    artifact_root: str | Path,
    sample_refs: Sequence[Mapping[str, Any]],
    target: Any,
    runtime_settings: Mapping[str, Any] | None,
    sample_step_id: str,
    proposal_step_id: str,
    update_step_id: str,
    proposal_function: str,
    proposal_input: Callable[[Any], Mapping[str, Any]],
    update_function: str,
    update_state: Callable[[Any, str, str | Path], dict[str, Any]],
) -> tuple[dict[str, Any] | None, DatabaseCreationBlocker | None, list[str], list[tuple[AnalysisReportOutcome, str]]]:
    if llm_port is None:
        return None, create_blocker(
            step_id=unavailable_step_id,
            function_or_route="analyze_samples",
            blocker_code="pipeline_capability_missing",
            recovery_state_class="support_only_unrecoverable",
            summary=unavailable_summary,
        ), [], []
    operations: list[str] = []
    reports: list[tuple[AnalysisReportOutcome, str]] = []
    analysis_run_id = analysis_id(workflow_run_id, analysis_suffix)
    try:
        sample_inputs, blocker = build_analyze_sample_inputs(
            target=target,
            sample_refs=sample_refs,
            step_id=sample_step_id,
            function_or_route="analyze_samples",
        )
        if blocker is not None:
            return None, blocker, operations, reports
        sample_result = run_llm(
            llm_port,
            "analyze_samples",
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            artifact_root=artifact_root,
            input_payload=sample_inputs,
            runtime_settings=runtime_settings,
        )
        operations.append("analyze_samples")
        blocker = blocker_from_llm_result(sample_step_id, sample_result)
        if blocker is not None:
            return None, blocker, operations, reports
        report = run_analysis_report(
            llm_port,
            "analyze_samples",
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            artifact_root=artifact_root,
            analysis_output=sample_result.output,
            runtime_settings=runtime_settings,
        )
        if report is not None:
            reports.append((report, analysis_run_id))
        proposal_result = run_llm(
            llm_port,
            proposal_function,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            artifact_root=artifact_root,
            input_payload=proposal_input(sample_result.output),
            runtime_settings=runtime_settings,
        )
        operations.append(proposal_function)
        blocker = blocker_from_llm_result(proposal_step_id, proposal_result)
        if blocker is not None:
            return None, blocker, operations, reports
        state = update_state(proposal_result.output, analysis_run_id, artifact_root)
        operations.append(update_function)
        return state, None, operations, reports
    except UpdateStateBuilderError as exc:
        return None, create_blocker(
            step_id=update_step_id,
            function_or_route=update_function,
            blocker_code="final_llm_validation_failure",
            recovery_state_class="final_llm_validation_failure",
            summary=str(exc),
        ), operations, reports
    except LLMAdapterError as exc:
        return None, create_blocker(
            step_id=sample_step_id,
            function_or_route="analyze_samples",
            blocker_code="pipeline_capability_missing",
            recovery_state_class="support_only_unrecoverable",
            summary=str(exc),
        ), operations, reports
