from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.types.database_creation import DatabaseCreationResumeContext, DatabaseCreationTarget
from semantic_control_kernel.types.state import WorkflowResumeState
from semantic_control_kernel.workflows.database_creation.semantic_release_staging import taxonomy_ref_from_staged_component


def build_resume_context(
    *,
    workflow_run_id: str,
    workflow_tool: str,
    last_completed_step_id: str,
    next_step_id: str,
    target: DatabaseCreationTarget,
    state_snapshot_id: str,
    final_state: str = "unknown",
    staged_component_refs: Sequence[Mapping[str, Any]] = (),
    allowed_continuation_workflow_tools: Sequence[str] = (),
) -> DatabaseCreationResumeContext:
    return DatabaseCreationResumeContext(
        workflow_run_id=workflow_run_id,
        workflow_tool=workflow_tool,
        last_completed_step_id=last_completed_step_id,
        next_step_id=next_step_id,
        target_identity=target.target_identity,
        state_snapshot_id=state_snapshot_id,
        final_state=final_state,
        target_payload=target.to_dict(),
        staged_component_refs=tuple(dict(item) for item in staged_component_refs),
        allowed_continuation_workflow_tools=tuple(allowed_continuation_workflow_tools),
    )


def persist_resume_context(store: WorkflowResumeStore, context: DatabaseCreationResumeContext) -> WorkflowResumeState:
    now = utc_iso()
    payload = {
        "schema_version": WorkflowResumeState.SCHEMA_VERSION,
        "workflow_run_id": context.workflow_run_id,
        "paused_function": context.next_step_id,
        "state_snapshot_identity": {
            "state_snapshot_id": context.state_snapshot_id,
            "schema_version": "state.snapshot_identity.v1",
        },
        "pending_confirmation_refs": [],
        "held_lock_refs": [],
        "selected_targets": [
            {
                "target_identity": context.target_identity,
                "database_creation_resume_context": context.to_dict(),
            }
        ],
        "next_expected_transition": {
            "next_step_id": context.next_step_id,
            "allowed_continuation_workflow_tools": list(context.allowed_continuation_workflow_tools),
        },
        "created_at": now,
        "updated_at": now,
    }
    resume_state = WorkflowResumeState.from_dict(payload)
    store.put_resume_state(resume_state)
    return resume_state


def extract_database_creation_resume_context(resume_state: WorkflowResumeState | Mapping[str, Any]) -> DatabaseCreationResumeContext:
    payload = resume_state.to_dict() if isinstance(resume_state, WorkflowResumeState) else dict(resume_state)
    for target in payload.get("selected_targets", ()):
        if isinstance(target, Mapping) and isinstance(target.get("database_creation_resume_context"), Mapping):
            return DatabaseCreationResumeContext.from_dict(target["database_creation_resume_context"])
    raise ValueError("Workflow resume state does not contain a Phase 9 database creation resume context.")


def resumable_context_for_tool(
    store: WorkflowResumeStore,
    workflow_tool: str,
) -> DatabaseCreationResumeContext | None:
    matches: list[DatabaseCreationResumeContext] = []
    for state in store.list_resumable():
        context = extract_database_creation_resume_context(state)
        if workflow_tool in context.allowed_continuation_workflow_tools:
            matches.append(context)
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f"Multiple resumable database creation contexts are available for {workflow_tool}.")
    return matches[0]


def resume_inputs_for_tool(
    workflow_tool: str,
    context: DatabaseCreationResumeContext,
) -> tuple[DatabaseCreationTarget, dict[str, Any], str, tuple[str, ...]]:
    if not context.target_payload:
        raise ValueError("Database creation resume context does not contain a target payload.")
    target = DatabaseCreationTarget.from_dict(context.target_payload)
    artifacts: dict[str, Any] = {"target": target.to_dict()}
    for ref in context.staged_component_refs:
        kind = str(ref.get("component_kind") or "")
        if kind == "taxonomy":
            artifacts["staged_taxonomy_ref"] = dict(ref)
            taxonomy_ref = taxonomy_ref_from_staged_component(ref)
            if taxonomy_ref:
                artifacts["taxonomy_ref"] = taxonomy_ref
        elif kind == "projections":
            artifacts["staged_projection_ref"] = dict(ref)

    completed_step_ids: tuple[str, ...] = ()
    if workflow_tool in {
        "empty_database_default_taxonomy_default_projections",
        "create_custom_taxonomy_path",
    } and context.final_state == "no_semantic_release":
        completed_step_ids = (
            "dc_collect_target",
            "dc_create_artifact_tree",
            "dc_store_artifact_tree",
            "dc_create_empty_database",
        )
    return target, artifacts, context.final_state, completed_step_ids


def resume_context_is_fresh(
    context: DatabaseCreationResumeContext,
    *,
    current_target_identity: Mapping[str, Any],
    current_staged_component_refs: Sequence[Mapping[str, Any]] = (),
) -> bool:
    if dict(context.target_identity) != dict(current_target_identity):
        return False
    expected = _component_fingerprints(context.staged_component_refs)
    current = _component_fingerprints(current_staged_component_refs)
    if expected and expected != current:
        return False
    return True


def assert_resume_context_fresh(
    context: DatabaseCreationResumeContext,
    *,
    current_target_identity: Mapping[str, Any],
    current_staged_component_refs: Sequence[Mapping[str, Any]] = (),
) -> None:
    if not resume_context_is_fresh(
        context,
        current_target_identity=current_target_identity,
        current_staged_component_refs=current_staged_component_refs,
    ):
        raise ValueError("database creation resume context is stale for the current target identity or staged components.")


def _component_fingerprints(refs: Sequence[Mapping[str, Any]]) -> tuple[tuple[str, str, str], ...]:
    pairs = []
    for ref in refs:
        kind = str(ref.get("component_kind", ""))
        stage_id = str(ref.get("stage_id", ""))
        fingerprint = str(ref.get("fingerprint", ""))
        if kind or stage_id or fingerprint:
            pairs.append((kind, stage_id, fingerprint))
    return tuple(sorted(pairs))
