from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.payloads import _blocker_summary

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _default_projectionless_summary(execution: "DatabaseCreationExecution") -> str:
    if "dc_create_empty_database" not in execution.completed_step_ids:
        prefix = "The default-taxonomy no-projections workflow stopped before the database shell completed. "
    elif "dc_attach_default_release" not in execution.completed_step_ids:
        prefix = "The empty database exists, but the default taxonomy path stopped before attach completed. "
    elif "dc_remove_default_projections" not in execution.completed_step_ids:
        prefix = "The empty database exists and the default Semantic Release was attached for preflight, but projection removal did not complete. "
    else:
        prefix = "Default projections were removed, but the incomplete release state was not finalized. "
    return prefix + f"Reason: {_blocker_summary(execution, 'The default-taxonomy no-projections workflow stopped before completion.')}"


def _custom_taxonomy_summary(execution: "DatabaseCreationExecution") -> str:
    if "dc_create_empty_database" not in execution.completed_step_ids and execution.workflow_tool.startswith("empty_database_"):
        prefix = "The custom-taxonomy no-projections workflow stopped before the database shell completed. "
    elif "tax_create_custom_taxonomy" not in execution.completed_step_ids:
        prefix = "The empty database exists, but custom taxonomy authoring stopped before taxonomy materialization completed. "
    elif "tax_stage_custom_taxonomy" not in execution.completed_step_ids:
        prefix = "The custom taxonomy was created, but it was not staged into the Semantic Release folder. "
    else:
        prefix = "The custom taxonomy was staged, but the incomplete release state was not finalized. "
    return prefix + f"Reason: {_blocker_summary(execution, 'The custom-taxonomy no-projections workflow stopped before completion.')}"


def _default_ready_summary(execution: "DatabaseCreationExecution") -> str:
    if "dc_create_empty_database" not in execution.completed_step_ids:
        prefix = "The ready-to-run empty database workflow stopped before the database shell completed. "
    elif "dc_activate_default_release" not in execution.completed_step_ids:
        prefix = "The empty database exists, but the default Semantic Release path stopped before activation completed. "
    else:
        prefix = "The default Semantic Release workflow stopped while writing the final notice. "
    return prefix + f"Reason: {_blocker_summary(execution, 'The ready-to-run empty database workflow stopped before completion.')}"


def _empty_database_restart_options() -> list[dict[str, Any]]:
    return [
        {
            "option_id": "restart_with_different_target",
            "user_label": "Start again with a different target",
            "meaning": "Run the same empty-database workflow again, but choose a different Artifact Tree name or database path.",
            "surface_availability": {
                "mode": "agent_tool_restart_path",
                "direct_agent_tool_available": True,
                "first_agent_tool": "empty_database_no_semantic_release",
            },
        },
        {
            "option_id": "repair_existing_binding_then_retry",
            "user_label": "Inspect the existing binding first",
            "meaning": "If the current target should be reused, inspect or repair the existing database/artifact binding before retrying.",
            "surface_availability": {"mode": "support_only_manual", "direct_agent_tool_available": False},
        },
    ]


def _agent_option(option_id: str, label: str, meaning: str, first_tool: str) -> dict[str, Any]:
    return {
        "option_id": option_id,
        "user_label": label,
        "meaning": meaning,
        "surface_availability": {"mode": "agent_tool", "direct_agent_tool_available": True, "first_agent_tool": first_tool},
    }
