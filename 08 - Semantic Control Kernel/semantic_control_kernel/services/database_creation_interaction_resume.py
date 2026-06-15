from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import taxonomy_ref_from_staged_component


@dataclass(frozen=True)
class DatabaseCreationInteractionResumeInputs:
    target: DatabaseCreationTarget | None
    artifacts: dict[str, Any]
    final_state: str
    completed_step_ids: tuple[str, ...]


def database_creation_interaction_resume_inputs(
    *,
    workflow_run_id: str,
    state_paths: StatePaths,
) -> DatabaseCreationInteractionResumeInputs:
    artifacts: dict[str, Any] = {}
    completed_step_ids: list[str] = []
    final_state = "unknown"
    for event in ProgressEventStore(state_paths).list_progress_events(workflow_run_id):
        payload = event.to_dict()
        state = str(payload.get("current_state_summary") or "")
        if state and state != "unknown":
            final_state = state
        step_id = str(payload.get("step_id") or "")
        status = str(payload.get("status") or "")
        refs = tuple(item for item in payload.get("artifact_refs", ()) if isinstance(item, Mapping))
        if status == "step_completed":
            if step_id and step_id != "dc_final_notice" and step_id not in completed_step_ids:
                completed_step_ids.append(step_id)
            _merge_artifact_refs(artifacts, step_id=step_id, artifact_refs=refs)
        elif status == "waiting_for_user":
            _merge_artifact_refs(artifacts, step_id=step_id, artifact_refs=refs)
    return DatabaseCreationInteractionResumeInputs(
        target=_target_from_artifacts(artifacts),
        artifacts=artifacts,
        final_state=final_state,
        completed_step_ids=tuple(completed_step_ids),
    )


def _merge_artifact_refs(
    artifacts: dict[str, Any],
    *,
    step_id: str,
    artifact_refs: tuple[Mapping[str, Any], ...],
) -> None:
    for ref in artifact_refs:
        schema_version = str(ref.get("schema_version") or "")
        if schema_version == "kernel.database_creation_target.v1":
            artifacts["target"] = dict(ref)
        if schema_version == "kernel.default_semantic_release_ref.v1":
            artifacts["default_release_ref"] = dict(ref)
        if schema_version == "kernel.default_taxonomy_projectionless_release_state.ref.v1":
            artifacts["projectionless_release_state_ref"] = dict(ref)
            artifacts["projectionless_release_state_path"] = str(ref.get("artifact_path") or "")
        _merge_component_ref(artifacts, ref)
        _merge_named_ref(artifacts, step_id=step_id, ref=ref)


def _merge_component_ref(artifacts: dict[str, Any], ref: Mapping[str, Any]) -> None:
    component_kind = str(ref.get("component_kind") or "")
    if component_kind == "taxonomy":
        artifacts["staged_taxonomy_ref"] = dict(ref)
        taxonomy_ref = taxonomy_ref_from_staged_component(ref)
        if taxonomy_ref:
            artifacts["taxonomy_ref"] = taxonomy_ref
    elif component_kind == "projections":
        artifacts["staged_projection_ref"] = dict(ref)


def _merge_named_ref(artifacts: dict[str, Any], *, step_id: str, ref: Mapping[str, Any]) -> None:
    taxonomy_ref = ref.get("taxonomy_ref")
    if isinstance(taxonomy_ref, Mapping):
        artifacts["taxonomy_ref"] = dict(taxonomy_ref)
    sample_refs = ref.get("sample_refs")
    if isinstance(sample_refs, list):
        key = "taxonomy_sample_refs" if step_id.startswith("tax_") else "projection_sample_refs"
        artifacts[key] = [dict(item) for item in sample_refs if isinstance(item, Mapping)]
    if step_id == "proj_build_authoring_view":
        artifacts["taxonomy_authoring_view"] = dict(ref)
    elif step_id == "proj_create_custom_projection":
        artifacts["custom_projection"] = dict(ref)
    elif step_id == "proj_validate_projection":
        artifacts["projection_validation"] = dict(ref)
    elif step_id == "rel_create_custom_release":
        artifacts["custom_release_ref"] = dict(ref)
    elif step_id == "dc_write_default_release" and ref.get("release_path"):
        artifacts["default_release_path"] = str(ref["release_path"])
    elif step_id == "rel_write_custom_release" and ref.get("release_path"):
        artifacts["custom_release_path"] = str(ref["release_path"])


def _target_from_artifacts(artifacts: Mapping[str, Any]) -> DatabaseCreationTarget | None:
    target = artifacts.get("target")
    if not isinstance(target, Mapping):
        return None
    try:
        return DatabaseCreationTarget.from_dict(target)
    except Exception:
        return None
