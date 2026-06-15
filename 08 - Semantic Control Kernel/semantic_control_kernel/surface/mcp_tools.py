from __future__ import annotations

from typing import Any

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_surface_service import AgentToolSurfaceService
from semantic_control_kernel.surface.mcp_tool_schemas import (
    AGENT_EMPTY_OBJECT_SCHEMA,
    EVENT_SCOPED_EMPTY_OBJECT_SCHEMA,
    EVENT_SCOPED_RECOVERY_TOOL_DESCRIPTION_MAP,
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_DESCRIPTION_MAP,
    PERMANENT_AGENT_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_SCHEMA_MAP,
)
from semantic_control_kernel.surface.mcp_visibility import tool_visibility
from semantic_control_kernel.types.mcp import (
    MCP_SCOPE_ALL,
    MCP_SCOPE_EVENT_SCOPED_RECOVERY,
    MCP_SCOPE_KERNEL_INTERNAL,
    MCP_SCOPE_PERMANENT_AGENT,
)


def list_mcp_tool_definitions(
    scope: str,
    *,
    state_paths: StatePaths | None = None,
    mirror_event_id: str | None = None,
) -> dict[str, Any]:
    definitions = {
        MCP_SCOPE_PERMANENT_AGENT: _permanent_agent_tool_definitions(),
        MCP_SCOPE_EVENT_SCOPED_RECOVERY: _event_scoped_tool_definitions(state_paths, mirror_event_id),
        MCP_SCOPE_KERNEL_INTERNAL: _kernel_internal_tool_definitions(),
    }
    if scope == MCP_SCOPE_ALL:
        combined = []
        for key in (MCP_SCOPE_PERMANENT_AGENT, MCP_SCOPE_EVENT_SCOPED_RECOVERY, MCP_SCOPE_KERNEL_INTERNAL):
            combined.extend(definitions[key])
        return {
            "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
            "scope": scope,
            "tool_definitions": combined,
        }
    return {
        "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
        "scope": scope,
        "tool_definitions": definitions.get(scope, []),
    }


def _permanent_agent_tool_definitions() -> list[dict[str, Any]]:
    return [
        _tool_definition(
            tool_name,
            PERMANENT_AGENT_TOOL_DESCRIPTION_MAP[tool_name],
            PERMANENT_AGENT_TOOL_SCHEMA_MAP.get(tool_name, AGENT_EMPTY_OBJECT_SCHEMA),
        )
        for tool_name in PERMANENT_AGENT_TOOL_NAMES
    ]


def _event_scoped_tool_definitions(
    state_paths: StatePaths | None,
    mirror_event_id: str | None,
) -> list[dict[str, Any]]:
    if state_paths is None or not mirror_event_id:
        visible_names = ()
    else:
        visible_names = tuple(
            tool.tool_name
            for tool in AgentToolSurfaceService(MirrorEventStore(state_paths)).list_event_scoped_tools(mirror_event_id)
        )
    return [
        _tool_definition(
            tool_name,
            EVENT_SCOPED_RECOVERY_TOOL_DESCRIPTION_MAP[tool_name],
            EVENT_SCOPED_EMPTY_OBJECT_SCHEMA,
        )
        for tool_name in visible_names
    ]


def _kernel_internal_tool_definitions() -> list[dict[str, Any]]:
    definitions = []
    for tool_name in KERNEL_INTERNAL_TOOL_NAMES + KERNEL_CONTINUATION_TOOL_NAMES:
        definitions.append(
            _tool_definition(
                tool_name,
                f"Kernel-owned {tool_visibility(tool_name).replace('_', ' ')} operation.",
                AGENT_EMPTY_OBJECT_SCHEMA,
            )
        )
    return definitions


def _tool_definition(tool_name: str, description: str, input_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool_name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": dict(input_schema.get("properties", {})),
            "required": list(input_schema.get("required", ())),
            "additionalProperties": bool(input_schema.get("additionalProperties", False)),
        },
    }
