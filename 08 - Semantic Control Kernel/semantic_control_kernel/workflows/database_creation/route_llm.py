from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.workflows.database_creation.route_sequences import get_step
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    complete_step,
    progress_started,
)
from semantic_control_kernel.workflows.llm_calls.progress_port import progress_reporting_llm_port
from semantic_control_kernel.workflows.llm_calls.user_reports import (
    analysis_report_mirror_payload,
    analysis_report_unavailable_mirror_payload,
)


def complete_llm_bundle(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    step_ids: tuple[str, ...],
    operations: tuple[str, ...],
    final_artifact: Mapping[str, Any] | None,
) -> None:
    for index, step_id in enumerate(step_ids):
        if step_id not in execution.completed_step_ids and index > 0:
            progress_started(repository, execution, step_id)
        operation = operations[index] if index < len(operations) else get_step(step_id).operation
        output_refs: list[Mapping[str, Any]] = []
        if index == len(step_ids) - 1 and final_artifact is not None:
            output_refs.append(dict(final_artifact))
        complete_step(
            repository,
            execution,
            step_id=step_id,
            function_name=operation,
            output_refs=output_refs,
        )


def emit_analysis_report_mirror(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    report_function: str,
    report_text: str,
    analysis_run_id: str,
    unavailable_detail: Mapping[str, Any] | None = None,
) -> None:
    text = str(report_text).strip()
    if not text and unavailable_detail is None:
        return
    if not text:
        repository.append_mirror(
            execution,
            **analysis_report_unavailable_mirror_payload(
                report_function=report_function,
                analysis_run_id=analysis_run_id,
                unavailable_detail=unavailable_detail,
            ),
        )
        return
    repository.append_mirror(
        execution,
        **analysis_report_mirror_payload(
            report_function=report_function,
            report_text=text,
            analysis_run_id=analysis_run_id,
        ),
    )


def progress_llm_port(
    llm_port: Any | None,
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    step_id_prefix: str = "llm",
) -> Any | None:
    if llm_port is None:
        return None
    return progress_reporting_llm_port(
        llm_port,
        append_progress=lambda **kwargs: repository.append_progress(execution, **kwargs),
        step_id_prefix=step_id_prefix,
    )
