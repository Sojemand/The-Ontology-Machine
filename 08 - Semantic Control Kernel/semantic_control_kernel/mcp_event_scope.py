from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.surface.mcp_visibility import is_event_scoped_tool
from semantic_control_kernel.validation.contract_validation import KernelContractError
from semantic_control_kernel.validation.mcp_validation import MCPContractError, require_hidden_scope, validate_mcp_request_envelope
from semantic_control_kernel.validation.recovery_validation import RECOVERY_TOOL_INPUT_FIELDS, assert_recovery_mirror_event


def check_event_scoped_tool(envelope: Mapping[str, Any], *, state_paths: StatePaths) -> dict[str, Any]:
    validate_mcp_request_envelope(envelope)
    tool_name = str(envelope["tool_name"])
    if not is_event_scoped_tool(tool_name):
        return {"allowed": False, "reason": "tool_is_not_event_scoped"}
    scope = require_hidden_scope(
        envelope.get("event_scope"),
        "mirror_event_id",
        "recovery_event_id",
        "state_snapshot_id",
        "client_request_id",
    )
    mirror_store = MirrorEventStore(state_paths)
    recovery_store = RecoveryEventStore(state_paths)
    try:
        mirror_event = mirror_store.get_mirror_event(scope["mirror_event_id"]).to_dict()
        recovery_event = recovery_store.get_recovery_event(scope["recovery_event_id"]).to_dict()
        availability = mirror_store.get_tool_availability(scope["mirror_event_id"]).to_dict()
    except ResumeStateNotFoundError as exc:
        return {"allowed": False, "reason": str(exc)}
    try:
        assert_recovery_mirror_event(mirror_event)
    except KernelContractError:
        return {"allowed": False, "reason": "mirror_event_invalid"}
    if recovery_event.get("mirror_event_id") != scope["mirror_event_id"]:
        return {"allowed": False, "reason": "mirror_event_mismatch"}
    if recovery_event.get("status") not in {"active", "support_only"}:
        return {"allowed": False, "reason": f"recovery_event_{recovery_event.get('status')}"}
    if availability.get("status") != "active":
        return {"allowed": False, "reason": f"tool_availability_{availability.get('status')}"}
    if is_expired(availability.get("expires_at")):
        return {"allowed": False, "reason": "tool_availability_expired"}
    if tool_name not in mirror_event.get("allowed_agent_tools", ()):
        return {"allowed": False, "reason": "tool_not_allowed_by_mirror"}
    if tool_name not in recovery_event.get("allowed_agent_tools", ()):
        return {"allowed": False, "reason": "tool_not_allowed_for_event"}
    if tool_name not in availability.get("allowed_agent_tools", ()):
        return {"allowed": False, "reason": "tool_not_available_for_mirror"}
    recovery_snapshot_id = state_snapshot_id(recovery_event.get("state_snapshot_identity"))
    if recovery_snapshot_id and recovery_snapshot_id != scope["state_snapshot_id"]:
        return {"allowed": False, "reason": "state_snapshot_mismatch"}
    return {
        "allowed": True,
        "reason": "",
        "workflow_run_id": recovery_event.get("workflow_run_id"),
        "mirror_event": mirror_event,
    }


def event_scoped_tool_payload(tool_name: str, event_scope: object) -> dict[str, Any]:
    required = RECOVERY_TOOL_INPUT_FIELDS.get(tool_name)
    if required is None:
        raise MCPContractError(f"Unknown event-scoped tool: {tool_name}")
    scope = require_hidden_scope(
        event_scope if isinstance(event_scope, Mapping) else None,
        *(field_name for field_name in required if field_name != "schema_version"),
    )
    payload = {"schema_version": f"kernel.{tool_name}.input.v1"}
    for field_name in required:
        if field_name == "schema_version":
            continue
        payload[field_name] = scope[field_name]
    return payload


def state_snapshot_id(payload: object) -> str:
    if isinstance(payload, Mapping):
        value = payload.get("state_snapshot_id")
        return str(value or "")
    return ""


def is_expired(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return True
    try:
        expires_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return expires_at <= datetime.now(timezone.utc)
