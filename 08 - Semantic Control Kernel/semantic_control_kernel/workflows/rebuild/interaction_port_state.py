from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventAck, UserInteractionRequest
from semantic_control_kernel.workflows.rebuild.interaction_port_identity import (
    clean_path,
    clean_text,
    rebuild_placeholder_identity,
)

REBUILD_INTERACTION_FUNCTIONS: tuple[str, ...] = (
    "choose_artifact_root_folder",
    "name_database",
    "user_confirmation",
)


class InlineClientFrontendEventSink(ClientFrontendEventSink):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        return ClientFrontendEventAck.from_dict(
            {
                "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
                "frontend_event_id": event.payload["frontend_event_id"],
                "accepted": True,
                "host_surface_identity": "semantic_control_kernel.inline_rebuild_interaction_port",
                "acknowledged_at": utc_iso(),
            }
        )


@dataclass(frozen=True)
class RebuildInteractionInputs:
    artifact_root: str
    target_database_name: str
    overwrite_receipt: dict[str, Any] | None = None


@dataclass(frozen=True)
class RebuildInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_overwrite_decision: str | None = None
    latest_existing_database_decision: str | None = None

    @property
    def next_interaction_function(self) -> str | None:
        if not self.artifact_root:
            return "choose_artifact_root_folder"
        if not self.target_database_name:
            return "name_database"
        return None


def build_user_interaction_service(
    state_paths: StatePaths,
    *,
    interaction_store: InteractionRequestStore,
    workflow_run_store: WorkflowRunStore,
    receipt_store: ReceiptStore,
) -> KernelUserInteractionService:
    return KernelUserInteractionService(
        interaction_store=interaction_store,
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(state_paths)),
        event_sink=InlineClientFrontendEventSink(),
        workflow_run_store=workflow_run_store,
        receipt_store=receipt_store,
    )


def ensure_workflow_run(
    workflow_run_store: WorkflowRunStore,
    workflow_tool: str,
    workflow_run_id: str,
) -> None:
    try:
        workflow_run_store.get_run(workflow_run_id)
    except ResumeStateNotFoundError:
        workflow_run_store.create_run(
            workflow_tool,
            rebuild_placeholder_identity(workflow_run_id),
            "kernel_database_rebuild_target_collection",
            workflow_run_id=workflow_run_id,
        )


def progress_from_recorded_responses(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> RebuildInteractionProgress:
    artifact_root: str | None = None
    target_database_name: str | None = None
    latest_overwrite_decision: str | None = None
    latest_existing_database_decision: str | None = None
    records = interaction_store.list_records_for_workflow(workflow_run_id)
    records.sort(key=lambda record: str(record.created_at))
    for record in records:
        request_payload = record.interaction_request if isinstance(record.interaction_request, Mapping) else {}
        response_payload = record.get("interaction_response", {}) if isinstance(record.get("interaction_response"), Mapping) else {}
        interaction_function = str(request_payload.get("interaction_function") or "")
        if record.status != "submitted" or interaction_function not in REBUILD_INTERACTION_FUNCTIONS:
            continue
        if interaction_function == "choose_artifact_root_folder":
            artifact_root = clean_path(response_payload.get("path_value"))
            continue
        if interaction_function == "name_database":
            target_database_name = clean_text(response_payload.get("text_value"))
            continue
        if interaction_function == "user_confirmation":
            confirmation_request_id = str(request_payload.get("confirmation_request_id") or "")
            decision = clean_text(response_payload.get("confirmation_decision"))
            if confirmation_request_id.startswith("rebuild_existing_corpus_db_warning:"):
                latest_existing_database_decision = decision
            elif confirmation_request_id.startswith("rebuild_overwrite:"):
                latest_overwrite_decision = decision
    return RebuildInteractionProgress(
        artifact_root=artifact_root,
        target_database_name=target_database_name,
        latest_overwrite_decision=latest_overwrite_decision,
        latest_existing_database_decision=latest_existing_database_decision,
    )


def pending_rebuild_request(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> UserInteractionRequest | None:
    for request in interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
        if request.payload.get("function_or_route") != "database_rebuild_from_artifacts":
            continue
        if request.payload.get("interaction_function") in REBUILD_INTERACTION_FUNCTIONS:
            return request
    return None


def pending_rebuild_request_ref(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> str | None:
    request = pending_rebuild_request(interaction_store, workflow_run_id)
    if request is None:
        return None
    return f"pending_interactions/active/{request.payload['interaction_request_id']}.json"


def pending_rebuild_summary(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> str:
    request = pending_rebuild_request(interaction_store, workflow_run_id)
    if request is None:
        return "The Kernel is waiting for database rebuild input."
    return str(request.payload.get("user_visible_summary") or "The Kernel is waiting for database rebuild input.")


__all__ = [
    "RebuildInteractionInputs",
    "RebuildInteractionProgress",
    "build_user_interaction_service",
    "ensure_workflow_run",
    "pending_rebuild_request",
    "pending_rebuild_request_ref",
    "pending_rebuild_summary",
    "progress_from_recorded_responses",
]
