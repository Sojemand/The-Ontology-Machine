from __future__ import annotations

from typing import Final


CLIENT_EVENTS_REQUEST_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.client_events_request.v1"
INTERACTION_RESPONSE_SUBMIT_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.interaction_response_submit.v1"
INTERACTION_CANCEL_REQUEST_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.interaction_cancel_request.v1"
EVENT_SCOPED_TOOL_DEFINITIONS_REQUEST_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.event_scoped_tool_definitions_request.v1"
EVENT_SCOPED_TOOL_DEFINITIONS_RESPONSE_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.event_scoped_tool_definitions_response.v1"
HOST_BRIDGE_RESPONSE_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.host_bridge_response.v1"

HOST_BRIDGE_RESPONSE_STATUSES: Final[tuple[str, ...]] = (
    "accepted",
    "rejected_stale",
    "cancelled",
    "closed",
    "expired",
    "failed",
)
