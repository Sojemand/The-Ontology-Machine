from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Mapping

from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker
from semantic_control_kernel.workflows.database_creation.resume import (
    build_resume_context,
    persist_resume_context as _owner_persist_resume_context,
)
from semantic_control_kernel.workflows.database_creation.route_state import default_release_ref
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import (
    incomplete_marker_payload,
    write_incomplete_marker,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    CreationStateRepository,
    DatabaseCreationExecution,
    block_execution,
)


def block_database_creation(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    blocker: DatabaseCreationBlocker,
    *,
    final_state: str,
) -> None:
    block_execution(repository, execution, blocker, final_state=final_state)
    if execution.target is not None and "dc_create_empty_database" in execution.completed_step_ids:
        resume_context = build_and_store_resume(repository, execution, next_step_id=blocker.step_id)
        write_incomplete_marker_if_possible(execution, resume_context, reason=blocker.blocker_code)


def build_and_store_resume(
    repository: CreationStateRepository,
    execution: DatabaseCreationExecution,
    *,
    next_step_id: str,
) -> Any:
    if execution.target is None:
        raise ValueError("Cannot persist Phase 9 resume context without a target.")
    resume_context = build_resume_context(
        workflow_run_id=execution.workflow_run_id,
        workflow_tool=execution.workflow_tool,
        last_completed_step_id=execution.completed_step_ids[-1] if execution.completed_step_ids else "",
        next_step_id=next_step_id,
        target=execution.target,
        state_snapshot_id=execution.state_snapshot_id,
        final_state=execution.final_state,
        staged_component_refs=staged_refs(execution),
        allowed_continuation_workflow_tools=allowed_continuations(execution),
    )
    _persist_resume_context(WorkflowResumeStore(repository.paths), resume_context)
    execution.resume_context = resume_context
    return resume_context


def _persist_resume_context(store: WorkflowResumeStore, resume_context: Any) -> None:
    routes_module = sys.modules.get("semantic_control_kernel.workflows.database_creation.routes")
    persist = getattr(routes_module, "persist_resume_context", _owner_persist_resume_context)
    persist(store, resume_context)


def write_incomplete_marker_if_possible(
    execution: DatabaseCreationExecution,
    resume_context: Any,
    *,
    reason: str = "semantic_release_incomplete",
) -> str | None:
    if execution.target is None or not Path(execution.target.semantic_release_path).exists():
        return None
    payload = incomplete_marker_payload(
        target=execution.target,
        workflow_run_id=execution.workflow_run_id,
        workflow_tool=execution.workflow_tool,
        missing_component_type=missing_component_type(execution),
        resume_context=resume_context,
        staged_components=staged_refs(execution),
        default_release_ref=default_release_ref(execution),
        projectionless_release_ref=execution.artifacts.get("projectionless_release_ref")
        if isinstance(execution.artifacts.get("projectionless_release_ref"), Mapping)
        else None,
        projectionless_release_state_ref=execution.artifacts.get("projectionless_release_state_ref")
        if isinstance(execution.artifacts.get("projectionless_release_state_ref"), Mapping)
        else None,
        reason=reason,
    )
    return write_incomplete_marker(target=execution.target, payload=payload)


def staged_refs(execution: DatabaseCreationExecution) -> tuple[Mapping[str, Any], ...]:
    refs = []
    for key in ("staged_taxonomy_ref", "staged_projection_ref"):
        value = execution.artifacts.get(key)
        if isinstance(value, Mapping):
            refs.append(dict(value))
    return tuple(refs)


def allowed_continuations(execution: DatabaseCreationExecution) -> tuple[str, ...]:
    if execution.final_state == "no_semantic_release":
        return (
            "empty_database_default_taxonomy_default_projections",
            "create_custom_taxonomy_path",
        )
    missing = missing_component_type(execution)
    if missing == "taxonomy":
        return ("create_custom_taxonomy_path",)
    if missing == "projections":
        return ("create_custom_projection_path",)
    return ()


def missing_component_type(execution: DatabaseCreationExecution) -> str:
    has_taxonomy = isinstance(execution.artifacts.get("staged_taxonomy_ref"), Mapping) or isinstance(
        execution.artifacts.get("taxonomy_ref"), Mapping
    )
    has_projection = isinstance(execution.artifacts.get("staged_projection_ref"), Mapping)
    if not has_taxonomy:
        return "taxonomy"
    if not has_projection:
        return "projections"
    return "write_attach_activate"


def next_missing_step(execution: DatabaseCreationExecution) -> str:
    missing = missing_component_type(execution)
    if missing == "taxonomy":
        return "tax_require_samples"
    if missing == "projections":
        return "proj_require_taxonomy"
    return "rel_create_custom_release"
