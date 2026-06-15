from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.next_steps import _blocked_inspection_next_step_options
from semantic_control_kernel.workflows.database_creation.final_notice.payloads import (
    _blocked_payload,
    _blocker_summary,
    _custom_taxonomy_blocked_fields,
    _default_release_blocked_fields,
    _kernel_persistence,
    _outcome,
    _projectionless_blocked_fields,
    _projectionless_outcome,
)
from semantic_control_kernel.workflows.database_creation.final_notice.blocked_summaries import (
    _agent_option,
    _custom_taxonomy_summary,
    _default_projectionless_summary,
    _default_ready_summary,
    _empty_database_restart_options,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _empty_database_no_semantic_release_blocked_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    prefix = (
        "The Artifact Tree was created, but the empty database setup stopped before completion. "
        if "dc_create_artifact_tree" in execution.completed_step_ids
        else "The empty database setup stopped before the required target could be provisioned. "
    )
    return _notice(
        execution,
        summary=prefix + f"Reason: {_blocker_summary(execution, 'The workflow stopped before the empty database setup completed.')}",
        outcome=_outcome(execution, semantic_release_attached=False, semantic_release_active=False, database_ready_for_ingest=False),
        attach_state_written=False,
        meaning="The workflow stopped before the empty database path reached a stable no-semantic-release state.",
        user_impact="The target is not ready for semantic extraction or ingestion. Resolve the blocker or restart with a different target.",
        next_step_options=_empty_database_restart_options(),
        extra_blocked_fields={"database_exists": "dc_create_empty_database" in execution.completed_step_ids},
        guidance_goal="Explain what the Kernel managed to create, why the workflow stopped, and what the user can do next.",
        guidance_must_include=[
            "workflow_blocked",
            "whether_artifact_tree_exists",
            "whether_empty_database_exists",
            "database_not_ready_for_ingest_yet",
        ],
    )

def _empty_database_default_taxonomy_no_projections_blocked_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _projectionless_notice(
        execution,
        custom_taxonomy=False,
        summary=_default_projectionless_summary(execution),
        guidance_goal="Explain why the default-taxonomy no-projections path stopped and which pieces are proven.",
        guidance_must_include=[
            "workflow_blocked",
            "whether_empty_database_exists",
            "whether_default_release_was_written",
            "whether_default_release_was_attached",
            "whether_default_projections_were_removed",
            "database_not_ready_for_ingest_yet",
        ],
    )


def _custom_taxonomy_no_projections_blocked_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _projectionless_notice(
        execution,
        custom_taxonomy=True,
        summary=_custom_taxonomy_summary(execution),
        guidance_goal="Explain why the custom-taxonomy no-projections path stopped and which pieces are proven.",
        guidance_must_include=[
            "workflow_blocked",
            "whether_empty_database_exists",
            "whether_custom_taxonomy_was_created",
            "whether_custom_taxonomy_was_staged",
            "database_not_ready_for_ingest_yet",
        ],
    )


def _empty_database_default_taxonomy_default_projections_blocked_notice(execution: "DatabaseCreationExecution") -> tuple[str, dict[str, Any]]:
    return _notice(
        execution,
        summary=_default_ready_summary(execution),
        outcome=_outcome(
            execution,
            semantic_release_attached="dc_attach_default_release" in execution.completed_step_ids,
            semantic_release_active=False,
            database_ready_for_ingest=False,
        ),
        attach_state_written="dc_attach_default_release" in execution.completed_step_ids,
        meaning="The workflow is the ready-to-run default path, but it stopped before the database reached semantic_release_active.",
        user_impact="The database must not be treated as ingest-ready until the blocker is resolved and activation is proven.",
        next_step_options=[
            _agent_option("kernel_status", "Inspect Kernel status", "Read the current Kernel state and latest blocker before retrying or repairing.", "kernel_status"),
            {
                "option_id": "restart_ready_to_run_database",
                "user_label": "Start ready database again",
                "meaning": "Create a fresh empty database with the complete default Semantic Release after choosing a non-conflicting target.",
                "surface_availability": {
                    "mode": "agent_tool_restart_path",
                    "direct_agent_tool_available": True,
                    "first_agent_tool": "empty_database_default_taxonomy_default_projections",
                },
            },
            {
                "option_id": "support_repair_existing_target",
                "user_label": "Repair existing target",
                "meaning": "If the current target must be reused, inspect adapter diagnostics and repair the failed owner boundary before retrying.",
                "surface_availability": {"mode": "support_only_manual", "direct_agent_tool_available": False},
            },
        ],
        extra_blocked_fields=_default_release_blocked_fields(execution),
        guidance_goal="Explain why the ready-to-run database path stopped and which proven pieces already exist.",
        guidance_must_include=[
            "workflow_blocked",
            "whether_empty_database_exists",
            "whether_default_release_was_written",
            "whether_default_release_was_attached",
            "database_not_ready_for_ingest_yet",
        ],
    )


def _projectionless_notice(
    execution: "DatabaseCreationExecution",
    *,
    custom_taxonomy: bool,
    summary: str,
    guidance_goal: str,
    guidance_must_include: list[str],
) -> tuple[str, dict[str, Any]]:
    return _notice(
        execution,
        summary=summary,
        outcome=_projectionless_outcome(execution),
        attach_state_written=(
            not custom_taxonomy
            and "dc_attach_default_release" in execution.completed_step_ids
            and "dc_remove_default_projections" not in execution.completed_step_ids
        ),
        meaning=(
            "This workflow is the custom-taxonomy, projections-later path. It is only stable when "
            "the custom taxonomy is staged and the incomplete Semantic Release state is persisted."
            if custom_taxonomy
            else "This workflow is the default-taxonomy, projections-later path. It is only stable when "
            "the default projections are removed and the projectionless release state is persisted."
        ),
        user_impact="The database must not be treated as ingest-ready. Inspect the blocker and continue only through Kernel resume state.",
        next_step_options=_blocked_inspection_next_step_options(),
        extra_blocked_fields=(
            _custom_taxonomy_blocked_fields(execution)
            if custom_taxonomy
            else _projectionless_blocked_fields(execution)
        ),
        guidance_goal=guidance_goal,
        guidance_must_include=guidance_must_include,
    )


def _notice(
    execution: "DatabaseCreationExecution",
    *,
    summary: str,
    outcome: dict[str, Any],
    attach_state_written: bool,
    meaning: str,
    user_impact: str,
    next_step_options: list[dict[str, Any]],
    extra_blocked_fields: dict[str, Any],
    guidance_goal: str,
    guidance_must_include: list[str],
) -> tuple[str, dict[str, Any]]:
    return summary, _blocked_payload(
        execution,
        outcome=outcome,
        kernel_persistence=_kernel_persistence(execution, attach_state_written=attach_state_written),
        state_meaning={"semantic_release_state": execution.final_state, "meaning": meaning, "user_impact": user_impact},
        next_step_options=next_step_options,
        extra_blocked_fields=extra_blocked_fields,
        guidance_goal=guidance_goal,
        guidance_must_include=guidance_must_include,
    )
