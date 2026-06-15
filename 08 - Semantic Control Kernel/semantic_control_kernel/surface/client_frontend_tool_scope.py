from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.surface.client_frontend_event_scope import (
    is_expired,
    latest_reset_created_at,
    mapping_is_after_reset_boundary,
    state_snapshot_id,
)
from semantic_control_kernel.surface.mcp_tools import list_mcp_tool_definitions
from semantic_control_kernel.types.client_frontend_bridge import EVENT_SCOPED_TOOL_DEFINITIONS_RESPONSE_SCHEMA_VERSION
from semantic_control_kernel.validation.client_frontend_bridge_validation import (
    validate_event_scoped_tool_definitions_request,
    validate_event_scoped_tool_definitions_response,
)


def list_event_scoped_tool_definitions(
    request: Mapping[str, Any],
    *,
    state_paths: StatePaths,
) -> dict[str, Any]:
    validate_event_scoped_tool_definitions_request(request)
    mirror_store = MirrorEventStore(state_paths)
    recovery_store = RecoveryEventStore(state_paths)
    mirror_event_id = str(request["mirror_event_id"])
    recovery_event_id = str(request["recovery_event_id"])
    requested_snapshot_id = str(request["state_snapshot_id"])
    tool_definitions: list[dict[str, Any]] = []
    status = "active"
    error: dict[str, Any] | None = None
    reset_boundary = latest_reset_created_at(state_paths)
    try:
        recovery_event = recovery_store.get_recovery_event(recovery_event_id).to_dict()
        availability = mirror_store.get_tool_availability(mirror_event_id).to_dict()
        if recovery_event.get("mirror_event_id") != mirror_event_id:
            status = "failed"
            error = {"code": "event_scope_mismatch", "safe_message": "Recovery event no longer matches the active mirror event."}
        elif not mapping_is_after_reset_boundary(recovery_event, reset_boundary, "created_at"):
            status = "failed"
            error = {"code": "event_scope_reset", "safe_message": "Recovery event scope was cleared by a Kernel reset."}
        elif not mapping_is_after_reset_boundary(availability, reset_boundary, "updated_at", "created_at"):
            status = "failed"
            error = {"code": "event_scope_reset", "safe_message": "Recovery tool availability was cleared by a Kernel reset."}
        elif recovery_event.get("status") not in {"active", "support_only"}:
            status = str(recovery_event.get("status") or "failed")
        elif recovery_event.get("expires_at") and is_expired(recovery_event.get("expires_at")):
            status = "expired"
            error = {"code": "event_scope_expired", "safe_message": "Recovery event scope has expired."}
        elif availability.get("status") != "active":
            status = str(availability.get("status") or "failed")
        elif is_expired(availability.get("expires_at")):
            status = "expired"
            error = {"code": "event_scope_expired", "safe_message": "Recovery tool availability has expired."}
        elif state_snapshot_id(recovery_event.get("state_snapshot_identity")) != requested_snapshot_id:
            status = "failed"
            error = {"code": "state_snapshot_mismatch", "safe_message": "Recovery event is stale for the current Kernel snapshot."}
        else:
            tool_definitions = list_mcp_tool_definitions(
                "event_scoped_recovery",
                state_paths=state_paths,
                mirror_event_id=mirror_event_id,
            )["tool_definitions"]
    except ResumeStateNotFoundError:
        status = "failed"
        error = {"code": "event_scope_missing", "safe_message": "The requested recovery scope is no longer active."}
    payload = {
        "schema_version": EVENT_SCOPED_TOOL_DEFINITIONS_RESPONSE_SCHEMA_VERSION,
        "mirror_event_id": mirror_event_id,
        "recovery_event_id": recovery_event_id,
        "state_snapshot_id": requested_snapshot_id,
        "status": status,
        "tool_definitions": tool_definitions,
    }
    if error is not None:
        payload["error"] = error
    validate_event_scoped_tool_definitions_response(payload)
    return payload
