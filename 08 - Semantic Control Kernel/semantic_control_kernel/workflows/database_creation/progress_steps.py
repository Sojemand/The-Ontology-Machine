from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, ProgressEventType, ProgressStatus
from semantic_control_kernel.types.receipts import OperationReceipt
from semantic_control_kernel.workflows.database_creation.execution_state import DatabaseCreationExecution
from semantic_control_kernel.workflows.database_creation.final_notice import (
    build_database_creation_final_notice,
)
from semantic_control_kernel.workflows.database_creation.state_repository import CreationStateRepository


def progress_started(repository: CreationStateRepository, execution: DatabaseCreationExecution, step_id: str) -> None:
    repository.append_progress(
        execution,
        step_id=step_id,
        status=ProgressStatus.STEP_STARTED.value,
        event_type=ProgressEventType.WORKFLOW_STEP.value,
        summary=f"{step_id} started.",
    )


def complete_step(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    step_id: str,
    function_name: str,
    final_state: str | None = None,
    output_refs: Sequence[Mapping[str, Any]] | None = None,
    pipeline_adapter_receipts: Sequence[Mapping[str, Any]] | None = None,
) -> OperationReceipt:
    if final_state is not None:
        execution.final_state = final_state
    receipt = repository.append_operation_receipt(
        execution,
        function_name=function_name,
        final_kernel_state=execution.final_state,
        output_artifact_refs=output_refs,
        pipeline_adapter_receipts=pipeline_adapter_receipts,
    )
    repository.append_progress(
        execution,
        step_id=step_id,
        status=ProgressStatus.STEP_COMPLETED.value,
        event_type=ProgressEventType.WORKFLOW_STEP.value,
        summary=f"{step_id} completed.",
        receipt_refs=[{"operation_receipt_id": receipt.payload["operation_receipt_id"]}],
        artifact_refs=output_refs,
    )
    execution.completed_step_ids.append(step_id)
    execution.operation_log.append(function_name)
    return receipt


def block_execution(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    blocker: DatabaseCreationBlocker,
    *,
    final_state: str,
) -> None:
    execution.status = "blocked"
    execution.final_state = final_state
    execution.blocked_step_id = blocker.step_id
    execution.blocker = blocker
    repository.append_progress(
        execution,
        step_id=blocker.step_id,
        status=ProgressStatus.BLOCKED.value,
        event_type=ProgressEventType.WORKFLOW_STEP.value,
        summary=blocker.user_visible_summary,
    )
    repository.append_mirror(
        execution,
        event_type=MirrorEventType.BLOCKER.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        summary=blocker.user_visible_summary,
    )


def final_notice(repository: CreationStateRepository, execution: DatabaseCreationExecution) -> None:
    if execution.status == "running":
        execution.status = "completed"
    event_type = MirrorEventType.WORKFLOW_COMPLETED.value if execution.status == "completed" else MirrorEventType.BLOCKER.value
    severity = MirrorSeverity.INFO.value if execution.status == "completed" else MirrorSeverity.WARNING.value
    summary, extra = build_database_creation_final_notice(execution)
    repository.append_progress(
        execution,
        step_id="dc_final_notice",
        status=ProgressStatus.COMPLETED.value if execution.status == "completed" else ProgressStatus.BLOCKED.value,
        event_type=ProgressEventType.WORKFLOW_STEP.value,
        summary=summary,
    )
    repository.append_mirror(
        execution,
        event_type=event_type,
        severity=severity,
        summary=summary,
        extra=extra,
    )
    if "dc_final_notice" not in execution.completed_step_ids:
        execution.completed_step_ids.append("dc_final_notice")
