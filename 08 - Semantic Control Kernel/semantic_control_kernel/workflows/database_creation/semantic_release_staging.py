from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.database_creation import (
    SEMANTIC_RELEASE_INCOMPLETE_MARKER,
    DatabaseCreationResumeContext,
    DatabaseCreationTarget,
    DefaultSemanticReleaseRef,
)
from semantic_control_kernel.workflows.database_creation.taxonomy_refs import (
    enriched_taxonomy_ref,
    staged_component_from_adapter_output,
    taxonomy_ref_from_staged_component,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import write_json_file


def incomplete_marker_payload(
    *,
    target: DatabaseCreationTarget,
    workflow_run_id: str,
    workflow_tool: str,
    missing_component_type: str,
    resume_context: DatabaseCreationResumeContext,
    staged_components: Sequence[Mapping[str, Any]] = (),
    default_release_ref: DefaultSemanticReleaseRef | None = None,
    projectionless_release_ref: Mapping[str, Any] | None = None,
    projectionless_release_state_ref: Mapping[str, Any] | None = None,
    reason: str = "semantic_release_incomplete",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "marker_kind": "incomplete_semantic_release",
        "marker_version": "phase9.v1",
        "created_at": utc_iso(),
        "workflow_run_id": workflow_run_id,
        "workflow_tool": workflow_tool,
        "target_identity": target.target_identity,
        "database_path": target.database_path,
        "artifact_root_path": target.artifact_root_path,
        "missing_component_type": missing_component_type,
        "reason": reason,
        "resume_context": resume_context.to_dict(),
        "staged_component_refs": [dict(item) for item in staged_components],
        "resume_options": list(resume_context.allowed_continuation_workflow_tools),
    }
    if default_release_ref is not None:
        payload["default_release_ref"] = default_release_ref.to_dict()
    if projectionless_release_ref is not None:
        payload["projectionless_release_ref"] = dict(projectionless_release_ref)
    if projectionless_release_state_ref is not None:
        payload["projectionless_release_state_ref"] = dict(projectionless_release_state_ref)
    return payload


def write_incomplete_marker(
    *,
    target: DatabaseCreationTarget,
    payload: Mapping[str, Any],
) -> str:
    marker_path = Path(target.semantic_release_path) / SEMANTIC_RELEASE_INCOMPLETE_MARKER
    write_json_file(marker_path, payload)
    return str(marker_path)


def projectionless_release_state_payload(
    *,
    target: DatabaseCreationTarget,
    workflow_run_id: str,
    workflow_tool: str,
    source_default_release_ref: Mapping[str, Any],
    projectionless_release_ref: Mapping[str, Any],
    taxonomy_ref: Mapping[str, Any],
    removed_projection_refs: Sequence[Mapping[str, Any]],
    adapter_receipt_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "kernel.default_taxonomy_projectionless_release_state.v1",
        "created_at": utc_iso(),
        "workflow_run_id": workflow_run_id,
        "workflow_tool": workflow_tool,
        "target_identity": target.target_identity,
        "artifact_root_path": target.artifact_root_path,
        "database_path": target.database_path,
        "semantic_release_path": target.semantic_release_path,
        "source_default_release_ref": dict(source_default_release_ref),
        "projectionless_release_ref": dict(projectionless_release_ref),
        "taxonomy_ref": dict(taxonomy_ref),
        "removed_projection_refs": [dict(item) for item in removed_projection_refs],
        "remaining_projection_refs": [],
        "missing_component_type": "projections",
        "completeness_state": "incomplete",
        "adapter_receipt_refs": [dict(item) for item in adapter_receipt_refs],
    }


def write_projectionless_release_state(
    *,
    target: DatabaseCreationTarget,
    payload: Mapping[str, Any],
) -> str:
    artifact_path = Path(taxonomy_stage_path(target, "default_taxonomy_without_projections")) / "projectionless_release_state.json"
    write_json_file(artifact_path, payload)
    return str(artifact_path)


def release_package_path(target: DatabaseCreationTarget, release_id: str) -> str:
    return str(Path(target.semantic_release_path) / "releases" / release_id)


def taxonomy_stage_path(target: DatabaseCreationTarget, stage_id: str) -> str:
    return str(Path(target.semantic_release_path) / "staged" / "taxonomy" / stage_id)


def projections_stage_path(target: DatabaseCreationTarget, stage_id: str) -> str:
    return str(Path(target.semantic_release_path) / "staged" / "projections" / stage_id)
