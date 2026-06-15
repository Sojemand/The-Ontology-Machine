from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.client_frontend_events import (
    ClientFrontendEvent,
    ClientFrontendEventAck,
    ClientFrontendEventBatch,
    make_client_frontend_event_batch,
    validate_client_frontend_event,
)


@dataclass
class FakeClientFrontendSink:
    accepted: bool = True
    host_surface_identity: str = "fake_client_frontend_sink"
    rejection_reason: str = "host_surface_unavailable"
    emitted_events: list[ClientFrontendEvent] = field(default_factory=list)
    emitted_acks: list[ClientFrontendEventAck] = field(default_factory=list)

    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        validate_client_frontend_event(event)
        self.emitted_events.append(event)
        payload = {
            "accepted": self.accepted,
            "acknowledged_at": utc_iso(),
            "frontend_event_id": event.payload["frontend_event_id"],
            "host_surface_identity": self.host_surface_identity,
            "schema_version": ClientFrontendEventAck.SCHEMA_VERSION,
        }
        if not self.accepted:
            payload["rejection_reason"] = self.rejection_reason
        ack = ClientFrontendEventAck.from_dict(payload)
        self.emitted_acks.append(ack)
        return ack

    def event_batch(self, cursor: str = "") -> ClientFrontendEventBatch:
        return make_client_frontend_event_batch(cursor or self.latest_cursor(), self.emitted_events)

    def latest_cursor(self) -> str:
        if not self.emitted_events:
            return ""
        return self.emitted_events[-1].payload["mirror_event_id"]

    def event_payloads(self) -> Sequence[dict]:
        return tuple(event.to_dict() for event in self.emitted_events)
