from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.services.agent_workflow_creation_runner import (
    include_optional_database_creation_resume,
    operation_receipt_id,
    sync_database_creation_workflow_run,
)
from semantic_control_kernel.services.resume_options import RESUME_CONTINUE_TOOL_NAME, ResumeOption
from semantic_control_kernel.types.agent_tools import AgentToolResult
from semantic_control_kernel.workflows.database_creation import run_database_creation_workflow
from semantic_control_kernel.workflows.database_creation.resume import resume_inputs_for_tool


def continue_database_creation_resume_option(
    option: ResumeOption,
    *,
    state_paths: StatePaths,
    store: WorkflowResumeStore,
    database_creation_runtime,
    result_from_execution,
) -> AgentToolResult:
    context = option.database_creation_context
    if context is None:
        return AgentToolResult(
            tool_name=RESUME_CONTINUE_TOOL_NAME,
            status="blocked",
            effect="none",
            user_visible_summary="The selected database creation resume option is incomplete.",
            error={"code": "resume_option_incomplete", "message": "The selected database creation resume option is incomplete."},
            active_state={"resume_option": option.to_dict()},
        )
    try:
        target, initial_artifacts, initial_final_state, initial_completed_step_ids = resume_inputs_for_tool(
            option.continuation_workflow_tool,
            context,
        )
    except Exception as exc:
        return AgentToolResult(
            tool_name=RESUME_CONTINUE_TOOL_NAME,
            status="blocked",
            effect="none",
            user_visible_summary="The selected database creation resume option could not be prepared.",
            error={"code": "resume_option_prepare_failed", "message": str(exc)},
            active_state={"resume_option": option.to_dict()},
        )
    execution = run_database_creation_workflow(
        option.continuation_workflow_tool,
        runtime=database_creation_runtime(state_paths),
        target=target,
        initial_artifacts=initial_artifacts,
        initial_final_state=initial_final_state,
        initial_completed_step_ids=initial_completed_step_ids,
        include_optional_steps=include_optional_database_creation_resume(
            option.continuation_workflow_tool,
            initial_final_state,
        ),
    )
    payload = execution.to_dict()
    sync_database_creation_workflow_run(payload, state_paths=state_paths)
    if str(payload.get("status") or "") in {"completed", "blocked", "waiting"}:
        try:
            store.mark_resume_consumed(option.workflow_run_id, operation_receipt_id(payload))
        except ResumeStateNotFoundError:
            pass
    base = result_from_execution(RESUME_CONTINUE_TOOL_NAME, payload, state_paths=state_paths)
    return AgentToolResult(
        tool_name=base.tool_name,
        status=base.status,
        effect=base.effect,
        user_visible_summary=continued_resume_summary(option, payload),
        workflow_run_id=base.workflow_run_id,
        mirror_event=base.mirror_event,
        resume_state=base.resume_state,
        active_state=base.active_state,
        error=base.error,
        implemented_by_phase=base.implemented_by_phase,
        extra={
            **dict(base.extra),
            "continued_workflow_tool": option.continuation_workflow_tool,
            "resume_option": option.to_dict(),
        },
    )


def continued_resume_summary(option: ResumeOption, execution: Mapping[str, Any]) -> str:
    status = str(execution.get("status") or "")
    workflow_tool = option.continuation_workflow_tool
    if status == "completed":
        return f"The Kernel continued the selected resumable workflow through {workflow_tool}."
    if status == "waiting":
        return "The Kernel continued the selected resumable workflow and is waiting for the next required user interaction."
    if status == "blocked":
        blocker = execution.get("blocker")
        if isinstance(blocker, Mapping) and blocker.get("user_visible_summary"):
            return str(blocker["user_visible_summary"])
        return f"The selected resumable workflow is blocked while continuing {workflow_tool}."
    return f"The Kernel started the selected resumable workflow through {workflow_tool}."


__all__ = ["continue_database_creation_resume_option", "continued_resume_summary"]
