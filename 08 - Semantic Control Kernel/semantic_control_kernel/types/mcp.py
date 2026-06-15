from __future__ import annotations

from typing import Final


MCP_REQUEST_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.mcp_request.v1"
MCP_RESPONSE_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.mcp_response.v1"
MCP_TOOL_DEFINITION_LIST_SCHEMA_VERSION: Final[str] = "semantic_control_kernel.mcp_tool_definition_list.v1"

MCP_SCOPE_PERMANENT_AGENT: Final[str] = "permanent_agent"
MCP_SCOPE_EVENT_SCOPED_RECOVERY: Final[str] = "event_scoped_recovery"
MCP_SCOPE_KERNEL_INTERNAL: Final[str] = "kernel_internal"
MCP_SCOPE_ALL: Final[str] = "all"

MCP_TOOL_SCOPES: Final[tuple[str, ...]] = (
    MCP_SCOPE_PERMANENT_AGENT,
    MCP_SCOPE_EVENT_SCOPED_RECOVERY,
    MCP_SCOPE_KERNEL_INTERNAL,
    MCP_SCOPE_ALL,
)

MCP_VISIBILITY_AGENT_VISIBLE: Final[str] = "agent_visible"
MCP_VISIBILITY_EVENT_SCOPED: Final[str] = "event_scoped"
MCP_VISIBILITY_KERNEL_INTERNAL: Final[str] = "kernel_internal"
MCP_VISIBILITY_KERNEL_CONTINUATION_SCOPED: Final[str] = "kernel_continuation_scoped"

MCP_TOOL_VISIBILITIES: Final[tuple[str, ...]] = (
    MCP_VISIBILITY_AGENT_VISIBLE,
    MCP_VISIBILITY_EVENT_SCOPED,
    MCP_VISIBILITY_KERNEL_INTERNAL,
    MCP_VISIBILITY_KERNEL_CONTINUATION_SCOPED,
)

MCP_RESPONSE_STATUSES: Final[tuple[str, ...]] = (
    "accepted",
    "running",
    "waiting_for_user",
    "completed",
    "blocked",
    "recovery_required",
    "failed",
    "rejected",
)

