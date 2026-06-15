from __future__ import annotations

from dataclasses import dataclass

from semantic_control_kernel.types.client_frontend_events import ClientFrontendEvent, ClientFrontendEventAck
from semantic_control_kernel.types.events import MirrorEvent, UserInteractionRequest, UserInteractionResponse
from semantic_control_kernel.types.receipts import ConfirmationReceipt


@dataclass(frozen=True)
class InteractionDispatchResult:
    request: UserInteractionRequest
    mirror_event: MirrorEvent
    frontend_event: ClientFrontendEvent
    ack: ClientFrontendEventAck
    workflow_marked_waiting: bool = False


@dataclass(frozen=True)
class InteractionResponseResult:
    response: UserInteractionResponse
    accepted: bool
    consumed_value: bool
    terminal_status: str
    recovery_state: str | None = None
    confirmation_receipt: ConfirmationReceipt | None = None
    mirror_event: MirrorEvent | None = None
