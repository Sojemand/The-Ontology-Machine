from __future__ import annotations

from typing import Any

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.events import UserInteractionRequest
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker
from semantic_control_kernel.workflows.rebuild.interaction_port_conflicts import handle_existing_database_conflict
from semantic_control_kernel.workflows.rebuild.interaction_port_identity import (
    clean_path,
    clean_text,
    existing_corpus_databases,
    input_blocker,
    rebuild_target_identity,
)
from semantic_control_kernel.workflows.rebuild.interaction_port_receipts import matching_overwrite_receipt
from semantic_control_kernel.workflows.rebuild.interaction_port_requests import (
    open_next_interaction,
    open_overwrite_confirmation,
)
from semantic_control_kernel.workflows.rebuild.interaction_port_state import (
    RebuildInteractionInputs,
    build_user_interaction_service,
    ensure_workflow_run,
    pending_rebuild_request as _pending_rebuild_request,
    pending_rebuild_request_ref as _pending_rebuild_request_ref,
    pending_rebuild_summary as _pending_rebuild_summary,
    progress_from_recorded_responses,
)
from semantic_control_kernel.workflows.rebuild.semantic_release_load import corpus_builder_load_semantic_release
from semantic_control_kernel.workflows.rebuild.target_path import resolve_target_database


class RebuildInteractionPort:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        semantic_release_adapter: Any,
        interaction_store: InteractionRequestStore | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        receipt_store: ReceiptStore | None = None,
        user_interaction_service: KernelUserInteractionService | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.semantic_release_adapter = semantic_release_adapter
        self.interaction_store = interaction_store or InteractionRequestStore(state_paths)
        self.workflow_run_store = workflow_run_store or WorkflowRunStore(state_paths)
        self.receipt_store = receipt_store or ReceiptStore(state_paths)
        self.user_interaction_service = user_interaction_service or build_user_interaction_service(
            state_paths,
            interaction_store=self.interaction_store,
            workflow_run_store=self.workflow_run_store,
            receipt_store=self.receipt_store,
        )

    def collect_rebuild_inputs(
        self,
        *,
        workflow_tool: str,
        workflow_run_id: str,
    ) -> RebuildInteractionInputs | RebuildWorkflowBlocker | None:
        ensure_workflow_run(self.workflow_run_store, workflow_tool, workflow_run_id)
        progress = progress_from_recorded_responses(self.interaction_store, workflow_run_id)
        if progress.next_interaction_function is not None:
            if self.pending_rebuild_request(workflow_run_id) is None:
                open_next_interaction(self.user_interaction_service, workflow_tool, workflow_run_id, progress)
            return None
        artifact_root = clean_path(progress.artifact_root)
        target_database_name = clean_text(progress.target_database_name)
        if artifact_root is None or target_database_name is None:
            return input_blocker("Rebuild Artifact Tree and database name must be collected through Kernel/UI state.")
        try:
            target_path, _target_identity = resolve_target_database(
                artifact_root=artifact_root,
                target_database_name=target_database_name,
            )
        except ValueError as exc:
            return RebuildWorkflowBlocker(
                blocker_code="invalid_target_path",
                step_id="resolving_target_database",
                function_or_route=workflow_tool,
                recovery_state_class="target_identity_changed",
                user_visible_summary=str(exc),
            )
        existing_databases = existing_corpus_databases(target_path.parent, excluding=target_path)
        if not target_path.exists() and existing_databases:
            result = handle_existing_database_conflict(
                workflow_run_store=self.workflow_run_store,
                user_interaction_service=self.user_interaction_service,
                has_pending_request=self.pending_rebuild_request(workflow_run_id) is not None,
                workflow_tool=workflow_tool,
                workflow_run_id=workflow_run_id,
                artifact_root=artifact_root,
                target_path=target_path,
                existing_databases=existing_databases,
                latest_decision=progress.latest_existing_database_decision,
            )
            if result is not True:
                return result
        if not target_path.exists():
            self.workflow_run_store.mark_run_running(
                workflow_run_id,
                target_identity=rebuild_target_identity(workflow_run_id, artifact_root, target_path),
                resume_state_ref="",
            )
            return RebuildInteractionInputs(artifact_root=artifact_root, target_database_name=target_database_name)
        loaded_release, _load_result, blocker = corpus_builder_load_semantic_release(
            self.semantic_release_adapter,
            artifact_root=artifact_root,
            target_database_path=target_path,
        )
        if blocker is not None or loaded_release is None:
            return blocker or input_blocker("Semantic Release identity could not be loaded for rebuild overwrite confirmation.")
        confirmation_identity = rebuild_target_identity(
            workflow_run_id,
            artifact_root,
            target_path,
            release_fingerprint=str(loaded_release["loaded_release_fingerprint"]),
        )
        receipt = matching_overwrite_receipt(
            self.receipt_store,
            confirmation_identity,
            artifact_root=artifact_root,
            target_database_path=target_path,
            loaded_release_fingerprint=str(loaded_release["loaded_release_fingerprint"]),
            workflow_run_id=workflow_run_id,
        )
        if receipt is not None:
            self.workflow_run_store.mark_run_running(
                workflow_run_id,
                target_identity=rebuild_target_identity(workflow_run_id, artifact_root, target_path),
                resume_state_ref="",
            )
            return RebuildInteractionInputs(
                artifact_root=artifact_root,
                target_database_name=target_database_name,
                overwrite_receipt=receipt,
            )
        if progress.latest_overwrite_decision and progress.latest_overwrite_decision != "confirmed":
            return RebuildWorkflowBlocker(
                blocker_code="confirmation_missing",
                step_id="confirming_overwrite",
                function_or_route=workflow_tool,
                recovery_state_class="rebuild_overwrite",
                user_visible_summary="Rebuild overwrite was not confirmed, so the existing target database was left unchanged.",
            )
        if self.pending_rebuild_request(workflow_run_id) is None:
            self.workflow_run_store.mark_run_running(
                workflow_run_id,
                target_identity=confirmation_identity,
                resume_state_ref="",
            )
            open_overwrite_confirmation(
                self.user_interaction_service,
                workflow_tool=workflow_tool,
                workflow_run_id=workflow_run_id,
                artifact_root=artifact_root,
                target_database_path=target_path,
                loaded_release=loaded_release,
                target_identity=confirmation_identity,
            )
        return None

    def pending_rebuild_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        return _pending_rebuild_request(self.interaction_store, workflow_run_id)

    def pending_rebuild_request_ref(self, workflow_run_id: str) -> str | None:
        return _pending_rebuild_request_ref(self.interaction_store, workflow_run_id)

    def pending_rebuild_summary(self, workflow_run_id: str) -> str:
        return _pending_rebuild_summary(self.interaction_store, workflow_run_id)
