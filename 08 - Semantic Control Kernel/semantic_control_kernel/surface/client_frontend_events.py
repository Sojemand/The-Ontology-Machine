from __future__ import annotations

from typing import Sequence

from semantic_control_kernel.services.client_frontend_event_sink import ClientFrontendEventSink
from semantic_control_kernel.types.client_frontend_events import (
    ClientFrontendEvent,
    ClientFrontendEventAck,
    ClientFrontendEventBatch,
    make_client_frontend_event_batch,
)


def emit_client_frontend_event(
    sink: ClientFrontendEventSink,
    event: ClientFrontendEvent,
) -> ClientFrontendEventAck:
    return sink.emit(event)


def build_client_frontend_event_batch(
    cursor: str,
    events: Sequence[ClientFrontendEvent],
) -> ClientFrontendEventBatch:
    return make_client_frontend_event_batch(cursor, events)
