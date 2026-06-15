from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.enums import ClientFrontendEventKind
from semantic_control_kernel.types.events import (
    ClientFrontendEvent,
    ClientFrontendEventAck,
    ClientFrontendEventBatch,
)
from semantic_control_kernel.validation.contract_validation import KernelContractError, validate_contract


EVENT_PAYLOAD_FIELD_BY_KIND: dict[str, str | None] = {
    ClientFrontendEventKind.INTERACTION_REQUEST.value: "interaction_request",
    ClientFrontendEventKind.PROGRESS_EVENT.value: "progress_event",
    ClientFrontendEventKind.MIRROR_EVENT.value: "mirror_event",
    ClientFrontendEventKind.TOOL_AVAILABILITY.value: "tool_availability",
    ClientFrontendEventKind.INTERACTION_RESOLVED.value: None,
}


def validate_client_frontend_event(event: ClientFrontendEvent | Mapping[str, Any]) -> None:
    payload = event.to_dict() if isinstance(event, ClientFrontendEvent) else dict(event)
    validate_contract(payload, expected_schema_version=ClientFrontendEvent.SCHEMA_VERSION)
    required_payload_field = EVENT_PAYLOAD_FIELD_BY_KIND[payload["frontend_event_kind"]]
    if required_payload_field is not None and required_payload_field not in payload:
        raise KernelContractError(
            f"{payload['frontend_event_kind']} events must include {required_payload_field}."
        )


def validate_client_frontend_event_ack(ack: ClientFrontendEventAck | Mapping[str, Any]) -> None:
    payload = ack.to_dict() if isinstance(ack, ClientFrontendEventAck) else dict(ack)
    validate_contract(payload, expected_schema_version=ClientFrontendEventAck.SCHEMA_VERSION)


def make_client_frontend_event_batch(cursor: str, events: Sequence[ClientFrontendEvent]) -> ClientFrontendEventBatch:
    payload = {
        "cursor": cursor,
        "events": [event.to_dict() for event in events],
        "schema_version": ClientFrontendEventBatch.SCHEMA_VERSION,
    }
    batch = ClientFrontendEventBatch.from_dict(payload)
    validate_contract(batch, expected_schema_version=ClientFrontendEventBatch.SCHEMA_VERSION)
    return batch
