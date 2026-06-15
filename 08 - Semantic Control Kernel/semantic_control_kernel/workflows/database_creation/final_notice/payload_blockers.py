from __future__ import annotations

from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.payload_outcomes import (
    _projections_missing,
    _taxonomy_present,
)

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _blocker_payload(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    blocker = execution.blocker
    return {
        "blocker_code": blocker.blocker_code if blocker is not None else "",
        "step_id": blocker.step_id if blocker is not None else execution.blocked_step_id or "",
        "function_or_route": blocker.function_or_route if blocker is not None else "",
        "summary": _blocker_summary(execution, "The workflow stopped before completion."),
        "recovery_state_class": blocker.recovery_state_class if blocker is not None else "",
    }


def _blocker_summary(execution: "DatabaseCreationExecution", fallback: str) -> str:
    return execution.blocker.user_visible_summary if execution.blocker is not None else fallback


def _default_release_blocked_fields(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    return {
        "database_exists": "dc_create_empty_database" in execution.completed_step_ids,
        "release_already_exported": "dc_export_default_release" in execution.completed_step_ids,
        "release_already_written": "dc_write_default_release" in execution.completed_step_ids,
        "release_already_attached": "dc_attach_default_release" in execution.completed_step_ids,
        "activation_failure_scope": {
            "activation_step_reached": execution.blocked_step_id == "dc_activate_default_release" or "dc_activate_default_release" in execution.completed_step_ids,
            "preflight_after_attach_passed": bool(execution.artifacts.get("default_activation_preflight_passed")),
            "owner_activation_call_started": bool(execution.artifacts.get("default_activation_owner_call_started")),
            "owner_side_materialization_completed": "dc_activate_default_release" in execution.completed_step_ids,
        },
    }


def _projectionless_blocked_fields(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    return {
        **_default_release_blocked_fields(execution),
        "projection_removal_step_reached": execution.blocked_step_id == "dc_remove_default_projections" or "dc_remove_default_projections" in execution.completed_step_ids,
        "default_projections_removed": "dc_remove_default_projections" in execution.completed_step_ids,
        "projectionless_release_state_written": bool(execution.artifacts.get("projectionless_release_state_path")),
        "state_class_at_block": execution.final_state,
        "taxonomy_present": _taxonomy_present(execution),
        "projections_missing": _projections_missing(execution),
    }


def _custom_taxonomy_blocked_fields(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    return {
        "database_exists": "dc_create_empty_database" in execution.completed_step_ids,
        "taxonomy_sample_selection_completed": "tax_require_samples" in execution.completed_step_ids,
        "taxonomy_analysis_completed": "tax_analyze_samples" in execution.completed_step_ids,
        "taxonomy_proposal_created": "tax_create_proposal" in execution.completed_step_ids,
        "taxonomy_update_state_created": "tax_build_update_state" in execution.completed_step_ids,
        "custom_taxonomy_created": "tax_create_custom_taxonomy" in execution.completed_step_ids,
        "custom_taxonomy_staged": "tax_stage_custom_taxonomy" in execution.completed_step_ids,
        "state_class_at_block": execution.final_state,
        "taxonomy_present": _taxonomy_present(execution),
        "projections_missing": _projections_missing(execution),
    }
