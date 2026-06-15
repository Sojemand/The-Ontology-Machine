from __future__ import annotations

from typing import Any, Callable

from .semantic_control_kernel_client import SemanticControlKernelClient
from . import semantic_control_kernel_client_frontend_bridge as _host_bridge
from .semantic_control_kernel_visibility import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)
from .semantic_control_kernel_visibility_validation import HOST_BRIDGE_TOKEN_FIELD


def _client() -> SemanticControlKernelClient:
    return SemanticControlKernelClient()


def _default_client_context(arguments: dict[str, Any]) -> dict[str, Any]:
    context = {
        "host_surface_identity": "mcp_server",
        "client_request_id": str(arguments.get("client_request_id") or "mcp_server"),
        "conversation_ref": str(arguments.get("conversation_ref") or ""),
        "turn_ref": str(arguments.get("turn_ref") or ""),
    }
    if arguments.get("resume_option_ref"):
        context["resume_option_ref"] = str(arguments["resume_option_ref"])
    return context


def _call_permanent(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _client().call_tool(
        tool_name=tool_name,
        visibility="agent_visible",
        model_arguments={},
        client_context=_default_client_context(arguments),
    )


def _call_event_scoped(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _client().call_tool(
        tool_name=tool_name,
        visibility="event_scoped",
        model_arguments={},
        client_context=_default_client_context(arguments),
        event_scope=dict(arguments),
    )


def _call_internal(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _client().call_tool(
        tool_name=tool_name,
        visibility="kernel_internal",
        model_arguments={},
        client_context=_default_client_context(arguments),
        event_scope=dict(arguments),
    )


def _call_continuation(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _client().call_tool(
        tool_name=tool_name,
        visibility="kernel_continuation_scoped",
        model_arguments={},
        client_context=_default_client_context(arguments),
        event_scope=dict(arguments),
    )


def _call_host_only(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = getattr(_host_bridge, tool_name, None)
    if not callable(handler):
        raise KeyError(f"Host-only Semantic Control Kernel bridge handler fehlt: {tool_name}")
    bridge_arguments = dict(arguments)
    bridge_arguments.pop(HOST_BRIDGE_TOKEN_FIELD, None)
    return handler(bridge_arguments)


def _register(name: str, fn: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        return fn(name, arguments)

    handler.__name__ = name
    globals()[name] = handler


for _name in PERMANENT_AGENT_TOOL_NAMES:
    _register(_name, _call_permanent)

for _name in EVENT_SCOPED_RECOVERY_TOOL_NAMES:
    _register(_name, _call_event_scoped)

for _name in KERNEL_INTERNAL_TOOL_NAMES:
    _register(_name, _call_internal)

for _name in KERNEL_CONTINUATION_TOOL_NAMES:
    _register(_name, _call_continuation)

for _name in HOST_ONLY_CLIENT_BRIDGE_NAMES:
    _register(_name, _call_host_only)


SEMANTIC_CONTROL_KERNEL_HANDLER_NAMES = (
    PERMANENT_AGENT_TOOL_NAMES
    + EVENT_SCOPED_RECOVERY_TOOL_NAMES
    + KERNEL_INTERNAL_TOOL_NAMES
    + KERNEL_CONTINUATION_TOOL_NAMES
    + HOST_ONLY_CLIENT_BRIDGE_NAMES
)
