from __future__ import annotations

from typing import Any

from .semantic_control_kernel_tool_groups import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    EVENT_SCOPED_TOOL_SCOPE_FIELDS,
    FORWARDABLE_CLIENT_CONTEXT_FIELDS,
    HOST_ONLY_CLIENT_BRIDGE_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_REQUIRED_FIELDS,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)
from .semantic_control_kernel_visibility_bridge import kernel_bridge_confirms_event_scope
from .semantic_control_kernel_visibility_validation import (
    clean,
    error_response,
    host_only_bridge_payload_allowed,
    host_only_bridge_token_allowed,
    missing_required_scope_fields,
    unexpected_scope_fields,
)


def tool_visibility(tool_name: str) -> str:
    name = clean(tool_name)
    if name in PERMANENT_AGENT_TOOL_NAMES:
        return "agent_visible"
    if name in EVENT_SCOPED_RECOVERY_TOOL_NAMES:
        return "event_scoped"
    if name in KERNEL_INTERNAL_TOOL_NAMES:
        return "kernel_internal"
    if name in KERNEL_CONTINUATION_TOOL_NAMES:
        return "kernel_continuation_scoped"
    if name in HOST_ONLY_CLIENT_BRIDGE_NAMES:
        return "host_only_client_bridge"
    if name in LEGACY_RETIRED_TOOL_NAMES:
        return "legacy_hidden"
    return "unknown"


def authorize_tool_call(tool_name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    name = clean(tool_name)
    classification = tool_visibility(name)
    payload = dict(arguments or {})
    if classification == "agent_visible":
        return {"response": None, "enforce_permissions": True}
    if classification == "legacy_hidden":
        return {"response": retired_surface_response(name), "enforce_permissions": False}
    if classification == "host_only_client_bridge":
        return _authorize_host_only_bridge(name, payload)
    if classification == "event_scoped":
        return _authorize_event_scoped_tool(name, payload)
    if classification == "kernel_internal":
        return {
            "response": error_response(
                name,
                code="kernel_internal_scope_required",
                safe_message="This canonical Kernel function requires a Kernel-issued internal call envelope.",
            ),
            "enforce_permissions": False,
        }
    if classification == "kernel_continuation_scoped":
        return {
            "response": error_response(
                name,
                code="continuation_scope_required",
                safe_message="This continuation-scoped operation requires a Kernel-issued continuation envelope.",
            ),
            "enforce_permissions": False,
        }
    return {"response": None, "enforce_permissions": True}


def retired_surface_response(tool_name: str) -> dict[str, Any]:
    response = error_response(
        tool_name,
        code="legacy_kernel_surface_retired",
        safe_message="The selected legacy Kernel surface is retired. Use the Semantic Control Kernel workflow surface instead.",
        status="rejected",
    )
    response["error"]["replacement_surface"] = "semantic_control_kernel"
    response["error"]["safe_next_actions"] = list(PERMANENT_AGENT_TOOL_NAMES)
    return response


def semantic_control_kernel_name_set() -> set[str]:
    return (
        set(PERMANENT_AGENT_TOOL_NAMES)
        | set(EVENT_SCOPED_RECOVERY_TOOL_NAMES)
        | set(KERNEL_INTERNAL_TOOL_NAMES)
        | set(KERNEL_CONTINUATION_TOOL_NAMES)
        | set(HOST_ONLY_CLIENT_BRIDGE_NAMES)
        | set(LEGACY_RETIRED_TOOL_NAMES)
    )


def _authorize_host_only_bridge(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    required = HOST_ONLY_CLIENT_BRIDGE_REQUIRED_FIELDS.get(name, ())
    if host_only_bridge_payload_allowed(payload, required) and host_only_bridge_token_allowed(payload):
        return {"response": None, "enforce_permissions": False}
    return {
        "response": error_response(
            name,
            code="host_only_bridge_not_agent_tool",
            safe_message="This Client Frontend bridge operation is host-only and is not callable as an Agent tool.",
        ),
        "enforce_permissions": False,
    }


def _authorize_event_scoped_tool(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    required = EVENT_SCOPED_TOOL_SCOPE_FIELDS.get(name)
    allowed = set(required or ()) | FORWARDABLE_CLIENT_CONTEXT_FIELDS
    unavailable = error_response(
        name,
        code="event_scoped_tool_not_available",
        safe_message="This recovery tool is visible only through an active Kernel mirror event.",
    )
    if required is None or missing_required_scope_fields(payload, required):
        return {"response": unavailable, "enforce_permissions": False}
    if unexpected_scope_fields(payload, allowed):
        return {
            "response": error_response(
                name,
                code="event_scoped_tool_not_available",
                safe_message="This recovery tool accepts only Kernel-issued event scope.",
            ),
            "enforce_permissions": False,
        }
    if not kernel_bridge_confirms_event_scope(name, payload):
        return {"response": unavailable, "enforce_permissions": False}
    return {"response": None, "enforce_permissions": False}
