from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("UserInteractionRequest", "kernel.user_interaction_request.v1"),
    ("UserInteractionResponse", "kernel.user_interaction_response.v1"),
    ("ClientFrontendEvent", "kernel.client_frontend_event.v1"),
    ("ClientFrontendEventAck", "kernel.client_frontend_event_ack.v1"),
    ("ClientFrontendEventBatch", "kernel.client_frontend_event_batch.v1"),
    ("ProgressEvent", "kernel.progress_event.v1"),
    ("MirrorEvent", "kernel.mirror_event.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))
