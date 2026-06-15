from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.types.mcp import (
    MCP_REQUEST_SCHEMA_VERSION,
    MCP_RESPONSE_SCHEMA_VERSION,
    MCP_RESPONSE_STATUSES,
    MCP_TOOL_DEFINITION_LIST_SCHEMA_VERSION,
    MCP_TOOL_SCOPES,
    MCP_TOOL_VISIBILITIES,
)


class MCPContractError(ValueError):
    pass


def validate_tool_definition_list(payload: Mapping[str, Any]) -> None:
    _require_mapping(payload, MCP_TOOL_DEFINITION_LIST_SCHEMA_VERSION)
    _require_exact_schema(payload, MCP_TOOL_DEFINITION_LIST_SCHEMA_VERSION)
    _require_string(payload, "scope")
    if payload["scope"] not in MCP_TOOL_SCOPES:
        raise MCPContractError(f"Unknown MCP scope: {payload['scope']!r}")
    tools = payload.get("tool_definitions")
    if not isinstance(tools, list):
        raise MCPContractError("tool_definitions must be a list.")
    for tool in tools:
        validate_tool_definition(tool)


def validate_tool_definition(payload: Mapping[str, Any]) -> None:
    _require_mapping(payload, "mcp_tool_definition")
    for field_name in ("name", "description"):
        _require_string(payload, field_name)
    schema = payload.get("inputSchema")
    if not isinstance(schema, Mapping):
        raise MCPContractError("Tool definitions require inputSchema.")
    if schema.get("type") != "object":
        raise MCPContractError("inputSchema.type must be object.")
    if not isinstance(schema.get("properties"), Mapping):
        raise MCPContractError("inputSchema.properties must be an object.")
    if schema.get("additionalProperties") is not False:
        raise MCPContractError("inputSchema.additionalProperties must be false.")


def validate_mcp_request_envelope(payload: Mapping[str, Any]) -> None:
    _require_mapping(payload, MCP_REQUEST_SCHEMA_VERSION)
    _require_exact_schema(payload, MCP_REQUEST_SCHEMA_VERSION)
    _require_string(payload, "transport")
    _require_string(payload, "tool_name")
    _require_string(payload, "visibility")
    if payload["visibility"] not in MCP_TOOL_VISIBILITIES:
        raise MCPContractError(f"Unknown MCP visibility: {payload['visibility']!r}")
    model_arguments = payload.get("model_arguments")
    if not isinstance(model_arguments, Mapping):
        raise MCPContractError("model_arguments must be an object.")
    client_context = payload.get("client_context")
    if not isinstance(client_context, Mapping):
        raise MCPContractError("client_context must be an object.")
    _require_string(client_context, "host_surface_identity")
    _require_string(client_context, "client_request_id")
    event_scope = payload.get("event_scope")
    if event_scope is not None and not isinstance(event_scope, Mapping):
        raise MCPContractError("event_scope must be null or an object.")


def validate_mcp_response_envelope(payload: Mapping[str, Any]) -> None:
    _require_mapping(payload, MCP_RESPONSE_SCHEMA_VERSION)
    _require_exact_schema(payload, MCP_RESPONSE_SCHEMA_VERSION)
    _require_string(payload, "status")
    if payload["status"] not in MCP_RESPONSE_STATUSES:
        raise MCPContractError(f"Unknown MCP response status: {payload['status']!r}")
    _require_string(payload, "tool_name")
    _require_string(payload, "effect")
    _require_string(payload, "user_visible_summary")
    error = payload.get("error")
    if error is not None:
        if not isinstance(error, Mapping):
            raise MCPContractError("error must be null or an object.")
        _require_string(error, "code")
        _require_string(error, "category")
        _require_string(error, "safe_message")


def require_hidden_scope(
    payload: Mapping[str, Any] | None,
    *required_fields: str,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise MCPContractError("Hidden scope is required.")
    scope = dict(payload)
    for field_name in required_fields:
        value = scope.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise MCPContractError(f"Hidden scope field {field_name!r} is required.")
    return scope


def _require_mapping(payload: Mapping[str, Any] | object, name: str) -> None:
    if not isinstance(payload, Mapping):
        raise MCPContractError(f"{name} must be an object.")


def _require_exact_schema(payload: Mapping[str, Any], schema_version: str) -> None:
    if payload.get("schema_version") != schema_version:
        raise MCPContractError(f"Expected schema_version {schema_version!r}.")


def _require_string(payload: Mapping[str, Any], field_name: str) -> None:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise MCPContractError(f"{field_name} must be a non-empty string.")

