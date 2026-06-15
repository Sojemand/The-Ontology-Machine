from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_workflow_recovery import (
    blocked_extra,
    semantic_recovery_for_blocked_execution,
)
from semantic_control_kernel.types.agent_tools import AgentToolResult


def result_from_execution(tool_name: str, execution: Mapping[str, Any], *, state_paths: StatePaths) -> AgentToolResult:
    status = str(execution.get("status") or "")
    workflow_run_id = string_or_none(execution.get("workflow_run_id"))
    resume_payload = execution.get("resume_state")
    if not isinstance(resume_payload, Mapping) or not resume_payload:
        resume_payload = execution.get("resume_context")
    resume_state = dict(resume_payload) if isinstance(resume_payload, Mapping) and resume_payload else None
    blocker = dict(execution["blocker"]) if isinstance(execution.get("blocker"), Mapping) else None
    if status == "blocked":
        summary = str((blocker or {}).get("user_visible_summary") or f"{tool_name} is blocked in the current Kernel state.")
        recovery = semantic_recovery_for_blocked_execution(tool_name, execution, blocker, state_paths)
        return AgentToolResult(
            tool_name=tool_name,
            status="blocked",
            effect="none",
            user_visible_summary=summary,
            workflow_run_id=workflow_run_id,
            mirror_event=recovery.mirror_event if recovery is not None else None,
            resume_state=resume_state,
            active_state=active_state_from_execution(execution),
            error={
                "code": str((blocker or {}).get("blocker_code") or "workflow_blocked"),
                "message": summary,
            },
            extra=blocked_extra(blocker, recovery),
        )
    effect = "workflow_completed" if status == "completed" else "workflow_started"
    if status == "waiting":
        artifacts = execution.get("artifacts")
        summary = str(
            artifacts.get("pending_interaction_summary")
            if isinstance(artifacts, Mapping)
            else ""
        ) or f"The Kernel is waiting for user input to continue {tool_name}."
    else:
        summary = f"The Kernel completed {tool_name}." if status == "completed" else f"The Kernel started {tool_name}."
    extra: dict[str, Any] = {}
    final_state = execution.get("final_state")
    if final_state is not None:
        extra["final_state"] = final_state
    completed_step_ids = execution.get("completed_step_ids")
    if isinstance(completed_step_ids, list):
        extra["completed_step_ids"] = list(completed_step_ids)
    return AgentToolResult(
        tool_name=tool_name,
        status="ok",
        effect=effect,
        user_visible_summary=summary,
        workflow_run_id=workflow_run_id,
        mirror_event=latest_mirror_event(execution),
        resume_state=resume_state,
        extra=extra,
    )


def missing_kernel_state_result(tool_name: str, message: str) -> AgentToolResult:
    return AgentToolResult(
        tool_name=tool_name,
        status="blocked",
        effect="none",
        user_visible_summary=message,
        error={"code": "input_missing", "message": message},
    )


def active_state_from_execution(execution: Mapping[str, Any]) -> Mapping[str, Any] | None:
    payload: dict[str, Any] = {}
    blocked_step_id = execution.get("blocked_step_id")
    if blocked_step_id is not None:
        payload["blocked_step_id"] = blocked_step_id
    final_state = execution.get("final_state")
    if final_state is not None:
        payload["final_state"] = final_state
    return payload or None


def latest_mirror_event(execution: Mapping[str, Any]) -> Mapping[str, Any] | None:
    mirror_events = execution.get("mirror_events")
    if not isinstance(mirror_events, list) or not mirror_events:
        return None
    latest = mirror_events[-1]
    if isinstance(latest, Mapping):
        return dict(latest)
    return None


def string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
