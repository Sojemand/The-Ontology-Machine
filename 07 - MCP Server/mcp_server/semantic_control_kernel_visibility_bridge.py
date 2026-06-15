from __future__ import annotations

from typing import Any


def kernel_bridge_confirms_event_scope(tool_name: str, payload: dict[str, Any]) -> bool:
    request = {
        "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
        "mirror_event_id": str(payload.get("mirror_event_id") or ""),
        "recovery_event_id": str(payload.get("recovery_event_id") or ""),
        "state_snapshot_id": str(payload.get("state_snapshot_id") or ""),
        "host_surface_identity": "mcp_server",
        "client_request_id": str(payload.get("client_request_id") or "mcp_server"),
    }
    try:
        from .semantic_control_kernel_client import SemanticControlKernelClient

        response = SemanticControlKernelClient().list_event_scoped_tool_definitions(request)
    except Exception:
        return False
    if str(response.get("status") or "") != "active":
        return False
    return tool_name in {str(tool.get("name") or "").strip() for tool in response.get("tool_definitions", []) if isinstance(tool, dict)}
