from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker
from semantic_control_kernel.workflows.rebuild.interaction_port_identity import rebuild_target_identity
from semantic_control_kernel.workflows.rebuild.interaction_port_requests import open_existing_database_warning


def handle_existing_database_conflict(
    *,
    workflow_run_store: WorkflowRunStore,
    user_interaction_service: KernelUserInteractionService,
    has_pending_request: bool,
    workflow_tool: str,
    workflow_run_id: str,
    artifact_root: str,
    target_path: Path,
    existing_databases: tuple[Path, ...],
    latest_decision: str | None,
) -> RebuildWorkflowBlocker | None | bool:
    target_identity = rebuild_target_identity(workflow_run_id, artifact_root, target_path)
    if latest_decision == "confirmed":
        workflow_run_store.mark_run_running(workflow_run_id, target_identity=target_identity, resume_state_ref="")
        return True
    if latest_decision:
        return RebuildWorkflowBlocker(
            blocker_code="target_conflict",
            step_id="confirming_existing_corpus_database",
            function_or_route=workflow_tool,
            recovery_state_class="target_identity_changed",
            user_visible_summary=(
                "The selected Artifact Tree already contains a different Corpus database. "
                "Rebuild was stopped before creating another database file."
            ),
            diagnostics=(
                {
                    "existing_database_paths": [str(path) for path in existing_databases],
                    "requested_target_database_path": str(target_path),
                },
            ),
        )
    workflow_run_store.mark_run_running(workflow_run_id, target_identity=target_identity, resume_state_ref="")
    if not has_pending_request:
        open_existing_database_warning(
            user_interaction_service,
            workflow_tool=workflow_tool,
            workflow_run_id=workflow_run_id,
            target_database_path=target_path,
            existing_database_paths=existing_databases,
            target_identity=target_identity,
        )
    return None


__all__ = ["handle_existing_database_conflict"]
