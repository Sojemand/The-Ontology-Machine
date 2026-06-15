from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_service import KernelUserInteractionService
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunTarget
from semantic_control_kernel.types.events import ClientFrontendEvent, ClientFrontendEventAck, UserInteractionRequest
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import manual_placeholder_identity
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_progress import MANUAL_PIPELINE_INTERACTION_FUNCTIONS


class InlineClientFrontendEventSink(ClientFrontendEventSink):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        return ClientFrontendEventAck.from_dict(
            {
                "accepted": True,
                "acknowledged_at": utc_iso(),
                "frontend_event_id": event.payload["frontend_event_id"],
                "host_surface_identity": "semantic_control_kernel.inline_manual_pipeline_interaction_port",
                "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
            }
        )


@dataclass(frozen=True)
class ManualPipelineInteractionInputs:
    target: PipelineRunTarget
    input_files: tuple[PipelineInputFile, ...]
    confirmation_receipt: dict[str, Any]


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
            manual_placeholder_identity(workflow_run_id),
            "kernel_manual_pipeline_target_collection",
            workflow_run_id=workflow_run_id,
        )


def pending_pipeline_request(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> UserInteractionRequest | None:
    for request in interaction_store.list_pending_interactions_for_workflow(workflow_run_id):
        if request.payload.get("function_or_route") != "manual_pipeline_run":
            continue
        if request.payload.get("interaction_function") in MANUAL_PIPELINE_INTERACTION_FUNCTIONS:
            return request
    return None


def pending_pipeline_request_ref(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> str | None:
    request = pending_pipeline_request(interaction_store, workflow_run_id)
    if request is None:
        return None
    return f"pending_interactions/active/{request.payload['interaction_request_id']}.json"


def pending_pipeline_summary(
    interaction_store: InteractionRequestStore,
    workflow_run_id: str,
) -> str:
    request = pending_pipeline_request(interaction_store, workflow_run_id)
    if request is None:
        return "The Kernel is waiting for manual pipeline run input."
    return str(request.payload.get("user_visible_summary") or "The Kernel is waiting for manual pipeline run input.")


__all__ = [
    "ManualPipelineInteractionInputs",
    "build_user_interaction_service",
    "ensure_workflow_run",
    "pending_pipeline_request",
    "pending_pipeline_request_ref",
    "pending_pipeline_summary",
]
