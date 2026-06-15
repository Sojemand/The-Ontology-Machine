from __future__ import annotations

from typing import Any


def _continue_after_interaction(workflow_run_id: str, workflow_tool: str) -> dict[str, object]:
    from semantic_control_kernel.services.agent_tool_workflow_dispatch import continue_workflow_after_interaction
    from semantic_control_kernel.surface.agent_invocation import default_state_paths
    from semantic_control_kernel.surface.client_frontend_continuation import append_background_continuation_terminal_progress

    paths = default_state_paths()
    try:
        result = continue_workflow_after_interaction(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            state_paths=paths,
        )
    except Exception as exc:
        _record_background_continuation_failure(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            exc=exc,
        )
        raise
    result_payload = result.to_dict() if result is not None else None
    append_background_continuation_terminal_progress(
        paths,
        workflow_run_id=workflow_run_id,
        workflow_tool=workflow_tool,
        result_status=str((result_payload or {}).get("status") or "not_applicable"),
        current_state_summary=str((result_payload or {}).get("final_state") or (result_payload or {}).get("effect") or ""),
    )
    return {
        "schema_version": "kernel.background_continuation_result.v1",
        "status": "completed" if result is not None else "not_applicable",
        "workflow_run_id": workflow_run_id,
        "workflow_tool": workflow_tool,
        "result": result_payload,
    }


def _record_background_continuation_failure(*, workflow_run_id: str, workflow_tool: str, exc: Exception) -> None:
    try:
        from semantic_control_kernel.repository.event_store import ProgressEventStore
        from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
        from semantic_control_kernel.repository.paths import utc_iso
        from semantic_control_kernel.repository.run_store import WorkflowRunStore
        from semantic_control_kernel.surface.agent_invocation import default_state_paths
        from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
        from semantic_control_kernel.types.events import ProgressEvent

        paths = default_state_paths()
        progress_store = ProgressEventStore(paths)
        failure_summary = _background_failure_summary(exc)
        progress_store.append_progress_event_with_next_sequence(
            {
                "schema_version": ProgressEvent.SCHEMA_VERSION,
                "workflow_run_id": workflow_run_id,
                "workflow_tool": workflow_tool,
                "step_id": "background_continuation",
                "step_label": "background_continuation",
                "event_type": ProgressEventType.WORKFLOW_STEP.value,
                "status": ProgressStatus.FAILED.value,
                "user_visible_summary": failure_summary,
                "current_state_summary": failure_summary,
                "timestamp": utc_iso(),
            }
        )
        try:
            WorkflowRunStore(paths).mark_run_failed(workflow_run_id)
        except ResumeStateNotFoundError:
            pass
    except Exception:
        pass


def _background_failure_summary(exc: Exception) -> str:
    detail = " ".join(str(exc).strip().split())
    if len(detail) > 500:
        detail = detail[:497].rstrip() + "..."
    if detail:
        return f"Kernel background continuation failed ({type(exc).__name__}): {detail}"
    return f"Kernel background continuation failed ({type(exc).__name__})."
