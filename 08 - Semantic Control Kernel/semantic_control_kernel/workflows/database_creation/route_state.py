from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.database_creation import (
    DatabaseCreationTarget,
    DefaultSemanticReleaseRef,
)
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import (
    taxonomy_ref_from_staged_component,
)
from semantic_control_kernel.workflows.database_creation.route_sequences import get_route
from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def default_release_ref(execution: DatabaseCreationExecution) -> DefaultSemanticReleaseRef | None:
    payload = execution.artifacts.get("default_release_ref")
    if isinstance(payload, Mapping):
        return DefaultSemanticReleaseRef.from_mapping(payload)
    return None


def resolve_taxonomy_ref(runtime: Any, execution: DatabaseCreationExecution) -> Mapping[str, Any] | None:
    for key in ("taxonomy_ref", "staged_taxonomy_ref"):
        value = execution.artifacts.get(key)
        if isinstance(value, Mapping):
            if key == "staged_taxonomy_ref" and isinstance(value.get("component_identity"), Mapping):
                return taxonomy_ref_from_staged_component(value)
            taxonomy_ref = dict(value)
            taxonomy_ref.setdefault("source", "active")
            return taxonomy_ref
    release_ref = default_release_ref(execution)
    if release_ref is not None:
        taxonomy_ref = dict(release_ref.taxonomy_ref)
        taxonomy_ref.setdefault("source", "active")
        return taxonomy_ref
    resolved = runtime.interaction_port.resolve_taxonomy_ref(
        workflow_tool=execution.workflow_tool,
        workflow_run_id=execution.workflow_run_id,
        target=execution.target,
        state=execution.artifacts,
    )
    if isinstance(resolved, Mapping):
        taxonomy_ref = dict(resolved)
        taxonomy_ref.setdefault("source", "active")
        return taxonomy_ref
    return resolved


def taxonomy_authoring_release_path(execution: DatabaseCreationExecution) -> str | None:
    candidates: list[Any] = [execution.artifacts.get("default_release_path")]
    staged = execution.artifacts.get("staged_taxonomy_ref")
    if isinstance(staged, Mapping):
        artifact_ref = staged.get("artifact_ref")
        if isinstance(artifact_ref, Mapping):
            candidates.append(artifact_ref.get("release_path"))
    projectionless = execution.artifacts.get("projectionless_release_ref")
    if isinstance(projectionless, Mapping):
        candidates.append(projectionless.get("release_path"))
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def creation_analysis_artifact_root(runtime: Any, execution: DatabaseCreationExecution) -> Path:
    if execution.target is not None:
        return Path(execution.target.semantic_release_path)
    return Path(runtime.state_root)


def final_state_for_completed_route(workflow_tool: str, current: str) -> str:
    if current != "unknown":
        return current
    return get_route(workflow_tool).final_state


def target_from_runtime(runtime: Any) -> DatabaseCreationTarget | None:
    target = getattr(runtime.interaction_port, "target", None)
    if isinstance(target, DatabaseCreationTarget):
        return target
    return None
