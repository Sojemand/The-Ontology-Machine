from __future__ import annotations

from semantic_control_kernel.surface.mcp_tool_schemas import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)


def tool_visibility(tool_name: str) -> str:
    name = str(tool_name or "").strip()
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


def is_permanent_agent_tool(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "agent_visible"


def is_event_scoped_tool(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "event_scoped"


def is_kernel_internal_tool(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "kernel_internal"


def is_kernel_continuation_tool(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "kernel_continuation_scoped"


def is_host_only_bridge_name(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "host_only_client_bridge"


def is_legacy_retired_name(tool_name: str) -> bool:
    return tool_visibility(tool_name) == "legacy_hidden"

