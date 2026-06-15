from __future__ import annotations

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.services.user_interaction_dispatch import InteractionDispatchMixin
from semantic_control_kernel.services.user_interaction_events import InteractionEventMixin
from semantic_control_kernel.services.user_interaction_models import (
    InteractionDispatchResult,
    InteractionResponseResult,
)
from semantic_control_kernel.services.user_interaction_requests import InteractionRequestMixin
from semantic_control_kernel.services.user_interaction_responses import InteractionResponseMixin


class KernelUserInteractionService(
    InteractionRequestMixin,
    InteractionEventMixin,
    InteractionResponseMixin,
    InteractionDispatchMixin,
):
    def __init__(
        self,
        *,
        interaction_store: InteractionRequestStore,
        mirror_event_service: KernelMirrorEventService,
        event_sink: ClientFrontendEventSink,
        workflow_run_store: WorkflowRunStore | None = None,
        receipt_store: ReceiptStore | None = None,
    ) -> None:
        self.interaction_store = interaction_store
        self.mirror_event_service = mirror_event_service
        self.event_sink = event_sink
        self.workflow_run_store = workflow_run_store
        self.receipt_store = receipt_store


__all__ = [
    "InteractionDispatchResult",
    "InteractionResponseResult",
    "KernelUserInteractionService",
]
