from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.blocked import (
    _custom_taxonomy_no_projections_blocked_notice,
    _empty_database_default_taxonomy_default_projections_blocked_notice,
    _empty_database_default_taxonomy_no_projections_blocked_notice,
    _empty_database_no_semantic_release_blocked_notice,
)
from semantic_control_kernel.workflows.database_creation.final_notice.completion import (
    _custom_taxonomy_no_projections_completion_notice,
    _empty_database_default_taxonomy_default_projections_completion_notice,
    _empty_database_default_taxonomy_no_projections_completion_notice,
    _empty_database_no_semantic_release_completion_notice,
)
from semantic_control_kernel.workflows.database_creation.final_notice.constants import (
    _DEFAULT_BLOCKED_STRUCTURE,
    _RESUMED_BLOCKED_STRUCTURE,
    _RESUMED_COMPLETION_STRUCTURE,
)
from semantic_control_kernel.workflows.database_creation.final_notice.payloads import (
    _agent_guidance,
    _artifact_path_summary,
    _blocker_payload,
    _blocker_summary,
    _workflow_explanation_context,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution

COMPLETION_NOTICES = {
    "empty_database_no_semantic_release": _empty_database_no_semantic_release_completion_notice,
    "empty_database_default_taxonomy_no_projections": _empty_database_default_taxonomy_no_projections_completion_notice,
    "empty_database_default_taxonomy_default_projections": _empty_database_default_taxonomy_default_projections_completion_notice,
}
BLOCKED_NOTICES = {
    "empty_database_no_semantic_release": _empty_database_no_semantic_release_blocked_notice,
    "empty_database_default_taxonomy_no_projections": _empty_database_default_taxonomy_no_projections_blocked_notice,
    "empty_database_default_taxonomy_default_projections": _empty_database_default_taxonomy_default_projections_blocked_notice,
}


def build_database_creation_final_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any] | None]:
    if execution.status not in {"running", "completed", "blocked"}:
        return f"{execution.workflow_tool} finished with {execution.final_state}.", None
    if _is_custom_taxonomy_projectionless(execution):
        return (
            _custom_taxonomy_no_projections_blocked_notice(execution)
            if execution.status == "blocked"
            else _custom_taxonomy_no_projections_completion_notice(execution)
        )
    specialized = (BLOCKED_NOTICES if execution.status == "blocked" else COMPLETION_NOTICES).get(execution.workflow_tool)
    return specialized(execution) if specialized is not None else _generic_database_creation_notice(execution)


def _is_custom_taxonomy_projectionless(execution: "DatabaseCreationExecution") -> bool:
    return execution.workflow_tool == "empty_database_custom_taxonomy_no_projections" or (
        execution.workflow_tool == "create_custom_taxonomy_path"
        and execution.final_state == "semantic_release_incomplete"
    )


def _generic_database_creation_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    blocked = execution.status == "blocked"
    focus = "workflow_blocked" if blocked else "workflow_completion"
    context = _workflow_explanation_context(execution)
    detail: dict[str, Any] = {
        "workflow_family": "database_creation",
        "workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "completed_step_ids": list(execution.completed_step_ids),
        "created_artifacts": _artifact_path_summary(execution),
        "workflow_explanation_context": context,
        "outcome": {
            "semantic_release_active": execution.final_state == "semantic_release_active",
            "database_ready_for_ingest": execution.final_state == "semantic_release_active",
        },
    }
    if blocked:
        detail["blocker"] = _blocker_payload(execution)
    return _generic_summary(execution, blocked), {
        "agent_explanation_guidance": _agent_guidance(
            context=context,
            goal=(
                "Explain why the Kernel database-creation run stopped and name the proven state."
                if blocked
                else "Explain that the Kernel database-creation run is finished and name what was done."
            ),
            style="brief_operational_summary_with_blocker_and_next_steps" if blocked else "brief_operational_summary_with_done_state",
            default_structure=_DEFAULT_BLOCKED_STRUCTURE if blocked else ["what_was_created", "performed_this_run", "what_the_current_state_means"],
            resumed_structure=_RESUMED_BLOCKED_STRUCTURE if blocked else _RESUMED_COMPLETION_STRUCTURE,
            must_include=(
                ["workflow_blocked", "final_state", "blocker", "created_artifacts"]
                if blocked
                else ["workflow_completed", "final_state", "performed_this_run", "created_artifacts"]
            ),
            focus_path=f"technical_detail_ref.{focus}",
            next_step_instruction={"explain_blocker_meaning": True} if blocked else {"state_that_work_is_finished": True, "include_created_artifact_paths": True},
            do_not_claim=(
                ["that the workflow completed successfully"]
                if blocked
                else ["that a Kernel dialog is still waiting for input", "that the workflow is still running"]
            ),
            workflow_explanation_context_path=f"technical_detail_ref.{focus}.workflow_explanation_context",
        ),
        "technical_detail_ref": {"kind": f"database_creation_{focus}", focus: detail},
    }


def _generic_summary(execution: "DatabaseCreationExecution", blocked: bool) -> str:
    if blocked:
        return f"{execution.workflow_tool} blocked at {execution.blocked_step_id or 'unknown_step'}: {_blocker_summary(execution, 'Database creation finished.')}"
    if execution.final_state != "semantic_release_active":
        return "Database creation finished."
    if "custom_projections" in execution.workflow_tool:
        return "Custom projection database creation is complete: Artifact Tree, empty Corpus DB, custom projections and active Semantic Release are ready."
    return "Database creation is complete: Artifact Tree, empty Corpus DB and active Semantic Release are ready."
