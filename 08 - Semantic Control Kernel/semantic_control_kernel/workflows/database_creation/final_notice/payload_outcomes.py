from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _outcome(execution: "DatabaseCreationExecution", *, semantic_release_attached: bool, semantic_release_active: bool, database_ready_for_ingest: bool) -> dict[str, bool]:
    return {
        "artifact_tree_created": "dc_create_artifact_tree" in execution.completed_step_ids,
        "empty_database_created": "dc_create_empty_database" in execution.completed_step_ids,
        "semantic_release_exported": "dc_export_default_release" in execution.completed_step_ids,
        "semantic_release_written": "dc_write_default_release" in execution.completed_step_ids,
        "semantic_release_attached": semantic_release_attached,
        "semantic_release_active": semantic_release_active,
        "database_ready_for_ingest": database_ready_for_ingest,
    }


def _projectionless_outcome(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    outcome = _outcome(execution, semantic_release_attached=False, semantic_release_active=False, database_ready_for_ingest=False)
    outcome.update(
        {
            "taxonomy_present": _taxonomy_present(execution),
            "projections_missing": _projections_missing(execution),
            "semantic_release_runnable": False,
            "projectionless_release_state_written": bool(execution.artifacts.get("projectionless_release_state_path")),
        }
    )
    return outcome


def _kernel_persistence(execution: "DatabaseCreationExecution", *, attach_state_written: bool) -> dict[str, bool]:
    return {
        "active_artifact_tree_ref_written": "dc_store_artifact_tree" in execution.completed_step_ids,
        "database_binding_written": "dc_create_empty_database" in execution.completed_step_ids,
        "default_release_ref_written": "dc_export_default_release" in execution.completed_step_ids,
        "default_release_artifact_written": "dc_write_default_release" in execution.completed_step_ids,
        "attach_state_written": attach_state_written,
        "attach_state_archived_after_projection_strip": bool(execution.artifacts.get("default_attach_state_archived_after_projection_strip")),
        "projectionless_release_state_written": bool(execution.artifacts.get("projectionless_release_state_path")),
        "custom_taxonomy_staged": "tax_stage_custom_taxonomy" in execution.completed_step_ids,
        "resume_state_written": execution.resume_context is not None,
    }


def _taxonomy_present(execution: "DatabaseCreationExecution") -> bool:
    if isinstance(execution.artifacts.get("staged_taxonomy_ref"), Mapping) or isinstance(execution.artifacts.get("taxonomy_ref"), Mapping):
        return True
    default_release_ref = execution.artifacts.get("default_release_ref")
    return isinstance(default_release_ref, Mapping) and isinstance(default_release_ref.get("taxonomy_ref"), Mapping)


def _projections_missing(execution: "DatabaseCreationExecution") -> bool:
    if isinstance(execution.artifacts.get("staged_projection_ref"), Mapping):
        return False
    if execution.artifacts.get("default_projection_refs") == []:
        return True
    return _taxonomy_present(execution) and execution.final_state == "semantic_release_incomplete"
