from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import MirrorEvent
from semantic_control_kernel.types.merge import MergeWorkflowExecution
from semantic_control_kernel.workflows.merge.final_notice_payload import (
    _created_artifacts,
    _kernel_persistence,
    _outcome,
    _source_count,
    _source_summaries,
    _workflow_explanation_context,
)


COMPLETION_ACTIONS: tuple[str, ...] = ("manual_pipeline_run", "kernel_status")


def append_merge_final_notice(execution: MergeWorkflowExecution) -> None:
    if _has_final_notice(execution):
        return
    blocked = execution.status == "blocked"
    focus = "workflow_blocked" if blocked else "workflow_completion"
    detail = _detail(execution, blocked=blocked)
    payload: dict[str, Any] = {
        "schema_version": MirrorEvent.SCHEMA_VERSION,
        "mirror_event_id": generate_id("mirror_event_id"),
        "mirror_source": "kernel",
        "is_kernel_auto_call": True,
        "event_type": MirrorEventType.BLOCKER.value if blocked else MirrorEventType.WORKFLOW_COMPLETED.value,
        "severity": MirrorSeverity.WARNING.value if blocked else MirrorSeverity.INFO.value,
        "user_visible_summary": _summary(execution, blocked=blocked),
        "current_state_summary": execution.final_state,
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "kernel_dialog_state": "not_required",
        "allowed_agent_tools": [] if blocked else list(COMPLETION_ACTIONS),
        "agent_explanation_guidance": _agent_guidance(execution, focus=focus, blocked=blocked),
        "technical_detail_ref": {
            "kind": f"database_merge_{focus}",
            focus: detail,
        },
    }
    event = MirrorEvent.from_dict(payload)
    _persist_mirror(execution, event)
    execution.mirror_events.append(event.to_dict())


def _has_final_notice(execution: MergeWorkflowExecution) -> bool:
    for event in execution.mirror_events:
        detail = event.get("technical_detail_ref")
        if isinstance(detail, Mapping) and str(detail.get("kind", "")).startswith("database_merge_workflow_"):
            return True
    return False


def _detail(execution: MergeWorkflowExecution, *, blocked: bool) -> dict[str, Any]:
    selection = execution.selection or {}
    route = str(selection.get("merge_route") or execution.workflow_tool)
    context = _workflow_explanation_context(execution)
    detail: dict[str, Any] = {
        "workflow_family": "database_merge",
        "workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "merge_run_id": execution.merge_run_id,
        "merge_route": route,
        "source_database_count": _source_count(selection),
        "source_databases": _source_summaries(selection),
        "completed_step_ids": list(execution.completed_step_ids),
        "created_artifacts": _created_artifacts(execution),
        "kernel_persistence": _kernel_persistence(execution),
        "outcome": _outcome(execution, route=route, blocked=blocked),
        "workflow_explanation_context": context,
    }
    if blocked and execution.blocker is not None:
        detail["blocker"] = execution.blocker.to_dict()
    if not blocked:
        detail["next_step_options"] = [
            {
                "action": action,
                "surface": "permanent_agent_tool",
                "safety": "available_after_active_merged_release",
            }
            for action in COMPLETION_ACTIONS
        ]
    return detail


def _agent_guidance(execution: MergeWorkflowExecution, *, focus: str, blocked: bool) -> dict[str, Any]:
    return {
        "response_mode": "explain_now",
        "technical_detail_focus_path": f"technical_detail_ref.{focus}",
        "workflow_explanation_context_path": f"technical_detail_ref.{focus}.workflow_explanation_context",
        "goal": (
            "Explain why the Kernel database-merge run stopped and name the proven state."
            if blocked
            else "Explain that the Kernel database-merge run is finished and name what was merged."
        ),
        "style": "brief_operational_summary_with_blocker_and_next_steps"
        if blocked
        else "brief_operational_summary_with_done_state",
        "must_include": (
            ["workflow_blocked", "final_state", "blocker", "merge_route"]
            if blocked
            else ["workflow_completed", "final_state", "merge_route", "created_artifacts"]
        ),
        "next_step_instruction": {"explain_blocker_meaning": True}
        if blocked
        else {"state_that_work_is_finished": True, "include_created_artifact_paths": True},
        "do_not_claim": (
            ["that the merge completed successfully"]
            if blocked
            else ["that a Kernel dialog is still waiting for input", "that the workflow is still running"]
        ),
    }


def _summary(execution: MergeWorkflowExecution, *, blocked: bool) -> str:
    if blocked:
        blocker_summary = execution.blocker.user_visible_summary if execution.blocker else "Merge workflow is blocked."
        return f"{execution.workflow_tool} blocked at {execution.blocked_step_id or 'unknown_step'}: {blocker_summary}"
    artifacts = _created_artifacts(execution)
    target_root = artifacts.get("target_artifact_root_path")
    target_db = artifacts.get("target_database_path")
    route = str((execution.selection or {}).get("merge_route") or execution.workflow_tool)
    route_label = "filled" if route == "filled_databases_merge_path" else "empty"
    suffix = f" Artifact Tree: {target_root}; database: {target_db}." if target_root and target_db else ""
    return f"Database merge is complete: {route_label} additive merge produced an active Semantic Release.{suffix}"


def _persist_mirror(execution: MergeWorkflowExecution, event: MirrorEvent) -> None:
    paths = StatePaths.from_state_root(Path(execution.state_root))
    paths.ensure_layout()
    MirrorEventStore(paths).append_mirror_event(event)
