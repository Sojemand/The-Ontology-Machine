from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.types.events import ProgressEvent


def mark_workflow_running(state_paths: StatePaths, workflow_run_id: str) -> None:
    try:
        WorkflowRunStore(state_paths).mark_run_running(workflow_run_id, resume_state_ref="")
    except ResumeStateNotFoundError:
        return


def should_continue_inline(pending_request: Mapping[str, Any], continue_inline: bool | None) -> bool:
    if continue_inline is not None:
        return continue_inline
    interaction_function = str(pending_request.get("interaction_function") or "")
    return interaction_function in {
        "choose_artifact_root_folder",
        "name_artifact_root_folder",
        "choose_merge_database_count",
        "choose_databases_to_merge",
        "choose_new_artifact_root_folder",
    }


def append_background_continuation_progress(
    state_paths: StatePaths,
    *,
    workflow_run_id: str,
    workflow_tool: str,
) -> None:
    progress_store = ProgressEventStore(state_paths)
    progress_store.append_progress_event_with_next_sequence(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": workflow_run_id,
            "workflow_tool": workflow_tool,
            "step_id": "kernel_background_continuation",
            "step_label": "kernel_background_continuation",
            "event_type": ProgressEventType.PIPELINE_STEP.value,
            "status": ProgressStatus.STEP_STARTED.value,
            "user_visible_summary": "Kernel workflow continuation started in the background.",
            "current_state_summary": "unknown",
            "timestamp": utc_iso(),
        }
    )


def append_background_continuation_terminal_progress(
    state_paths: StatePaths,
    *,
    workflow_run_id: str,
    workflow_tool: str,
    result_status: str,
    current_state_summary: str = "",
) -> None:
    progress_store = ProgressEventStore(state_paths)
    status = _terminal_progress_status(result_status)
    progress_store.append_progress_event_with_next_sequence(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": workflow_run_id,
            "workflow_tool": workflow_tool,
            "step_id": "kernel_background_continuation",
            "step_label": "kernel_background_continuation",
            "event_type": ProgressEventType.PIPELINE_STEP.value,
            "status": status,
            "user_visible_summary": _terminal_summary(status),
            "current_state_summary": current_state_summary or status,
            "timestamp": utc_iso(),
        }
    )


def _terminal_progress_status(result_status: str) -> str:
    if result_status in {"ok", "completed", "workflow_completed", "not_applicable"}:
        return ProgressStatus.COMPLETED.value
    if result_status == "blocked":
        return ProgressStatus.BLOCKED.value
    if result_status in {"cancelled", "canceled"}:
        return ProgressStatus.CANCELLED.value
    return ProgressStatus.FAILED.value


def _terminal_summary(status: str) -> str:
    if status == ProgressStatus.COMPLETED.value:
        return "Kernel workflow continuation completed in the background."
    if status == ProgressStatus.BLOCKED.value:
        return "Kernel workflow continuation blocked in the background."
    if status == ProgressStatus.CANCELLED.value:
        return "Kernel workflow continuation was cancelled in the background."
    return "Kernel workflow continuation failed in the background."
