from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventAck, UserInteractionRequest
from semantic_control_kernel.workflows.database_creation.interaction_helpers import (
    CREATION_TARGET_INTERACTION_FUNCTIONS,
    SAMPLE_FILE_INTERACTION_FUNCTION,
    creation_target_placeholder_identity,
    creation_target_progress_from_records,
    interaction_snapshot_id,
    prefilled_values_for,
    sample_target_identity,
    summary_for,
    title_for,
)
from semantic_control_kernel.workflows.database_creation.sample_input_adapter import sample_refs_from_input


class _InlineClientFrontendEventSink(ClientFrontendEventSink):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        return ClientFrontendEventAck.from_dict(
            {
                "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
                "frontend_event_id": event.payload["frontend_event_id"],
                "accepted": True,
                "host_surface_identity": "semantic_control_kernel.inline_interaction_port",
                "acknowledged_at": utc_iso(),
            }
        )


class DatabaseCreationInteractionPort:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        interaction_store: InteractionRequestStore | None = None,
        workflow_run_store: WorkflowRunStore | None = None,
        user_interaction_service: KernelUserInteractionService | None = None,
        orchestrator_adapter: Any | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.interaction_store = interaction_store or InteractionRequestStore(state_paths)
        self.workflow_run_store = workflow_run_store or WorkflowRunStore(state_paths)
        self.orchestrator_adapter = orchestrator_adapter
        self.user_interaction_service = user_interaction_service or KernelUserInteractionService(
            interaction_store=self.interaction_store,
            mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
            event_sink=_InlineClientFrontendEventSink(),
            workflow_run_store=self.workflow_run_store,
        )

    def collect_creation_target(self, *, workflow_tool: str, workflow_run_id: str) -> DatabaseCreationTarget | None:
        self._ensure_workflow_run(workflow_tool, workflow_run_id)
        progress = creation_target_progress_from_records(self.interaction_store.list_records_for_workflow(workflow_run_id))
        if progress.next_interaction_function is None:
            target = DatabaseCreationTarget.from_selection(
                artifact_root_parent=Path(progress.artifact_root_path).parent,
                artifact_root_name=Path(progress.artifact_root_path).name,
                database_name=str(progress.database_name or ""),
            )
            self.workflow_run_store.mark_run_running(workflow_run_id, target_identity=target.target_identity, resume_state_ref="")
            return target
        if self.pending_creation_target_request(workflow_run_id) is None:
            self._open_next_interaction(workflow_tool, workflow_run_id, progress)
        return None

    def pending_creation_target_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        for request in self.interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
            if request.payload.get("interaction_function") in CREATION_TARGET_INTERACTION_FUNCTIONS:
                return request
        return None

    def pending_creation_target_request_ref(self, workflow_run_id: str) -> str | None:
        request = self.pending_creation_target_request(workflow_run_id)
        if request is None:
            return None
        interaction_request_id = str(request.payload["interaction_request_id"])
        return f"pending_interactions/active/{interaction_request_id}.json"

    def pending_creation_target_summary(self, workflow_run_id: str) -> str:
        request = self.pending_creation_target_request(workflow_run_id)
        if request is None:
            return "The Kernel is waiting for database creation input."
        return str(request.payload.get("user_visible_summary") or "The Kernel is waiting for database creation input.")

    def select_sample_files(self, *, workflow_tool: str, workflow_run_id: str, purpose: str, target: DatabaseCreationTarget | None) -> tuple[Mapping[str, Any], ...]:
        if target is None:
            return ()
        self._ensure_workflow_run(workflow_tool, workflow_run_id)
        self.workflow_run_store.mark_run_running(workflow_run_id, target_identity=sample_target_identity(target), resume_state_ref="")
        if not self._sample_files_confirmed(workflow_run_id):
            if self.pending_sample_files_request(workflow_run_id) is None:
                self._open_sample_files_interaction(workflow_tool, workflow_run_id, target, purpose)
            return ()
        return sample_refs_from_input(target=target, orchestrator_adapter=self.orchestrator_adapter, workflow_run_id=workflow_run_id)

    def pending_sample_files_request(self, workflow_run_id: str) -> UserInteractionRequest | None:
        for request in self.interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
            if request.payload.get("interaction_function") == SAMPLE_FILE_INTERACTION_FUNCTION:
                return request
        return None

    def resolve_taxonomy_ref(self, *, workflow_tool: str, workflow_run_id: str, target: DatabaseCreationTarget | None, state: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return None

    def _ensure_workflow_run(self, workflow_tool: str, workflow_run_id: str) -> None:
        try:
            self.workflow_run_store.get_run(workflow_run_id)
        except ResumeStateNotFoundError:
            self.workflow_run_store.create_run(
                workflow_tool,
                creation_target_placeholder_identity(workflow_run_id),
                "kernel_database_creation_target_collection",
                workflow_run_id=workflow_run_id,
            )

    def _open_next_interaction(self, workflow_tool: str, workflow_run_id: str, progress) -> None:
        interaction_function = str(progress.next_interaction_function or "choose_artifact_root_folder")
        self.user_interaction_service.request_interaction(
            interaction_function=interaction_function,
            workflow_run_id=workflow_run_id,
            function_or_route=workflow_tool,
            target_identity=creation_target_placeholder_identity(workflow_run_id),
            state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, interaction_function)},
            user_visible_title=title_for(interaction_function),
            user_visible_summary=summary_for(interaction_function, progress),
            prefilled_values=prefilled_values_for(interaction_function, progress),
        )

    def _open_sample_files_interaction(self, workflow_tool: str, workflow_run_id: str, target: DatabaseCreationTarget, purpose: str) -> None:
        purpose_label = "taxonomy" if purpose == "taxonomy" else "projection"
        self.user_interaction_service.request_interaction(
            interaction_function=SAMPLE_FILE_INTERACTION_FUNCTION,
            workflow_run_id=workflow_run_id,
            function_or_route=workflow_tool,
            target_identity=sample_target_identity(target),
            state_snapshot_identity={"state_snapshot_id": interaction_snapshot_id(workflow_run_id, SAMPLE_FILE_INTERACTION_FUNCTION)},
            user_visible_title="Select Sample Files",
            user_visible_summary=f"Place the raw {purpose_label} sample files in the Artifact Tree Input folder, then confirm that samples are present.",
            prefilled_values={"input_path": target.input_path, "sample_purpose": purpose_label},
        )

    def _sample_files_confirmed(self, workflow_run_id: str) -> bool:
        records = self.interaction_store.list_records_for_workflow(workflow_run_id)
        records.sort(key=lambda record: str(record.created_at))
        for record in records:
            request_payload = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
            response_payload = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
            if record.status == "submitted" and request_payload.get("interaction_function") == SAMPLE_FILE_INTERACTION_FUNCTION:
                return response_payload.get("confirmation_decision") == "confirmed"
        return False
