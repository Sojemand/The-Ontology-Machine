from __future__ import annotations

from mcp_server.tool_handlers import call_tool
from mcp_server.tools import visible_tool_definitions


def test_host_bridge_tools_stay_out_of_normal_agent_surface() -> None:
    visible_names = {str(tool["name"]) for tool in visible_tool_definitions()}
    assert "kernel_list_client_frontend_events" not in visible_names
    assert "kernel_submit_user_interaction_response" not in visible_names
    assert "kernel_cancel_user_interaction" not in visible_names
    assert "kernel_list_event_scoped_tool_definitions" not in visible_names

    response = call_tool("kernel_list_client_frontend_events", {"client_request_id": "x"})
    assert response["error"]["code"] == "host_only_bridge_not_agent_tool"


def test_host_bridge_tools_reject_full_frontend_bridge_payload_without_host_token(monkeypatch) -> None:
    monkeypatch.delenv("VISION_MCP_HOST_BRIDGE_TOKEN", raising=False)
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client_frontend_bridge.kernel_list_client_frontend_events",
        lambda request: {
            "schema_version": "kernel.client_frontend_event_batch.v1",
            "cursor": str(request.get("cursor") or "0"),
            "events": [],
        },
    )

    response = call_tool(
        "kernel_list_client_frontend_events",
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "",
            "limit": 10,
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "client_a",
            "client_request_id": "req_events",
        },
    )

    assert response["error"]["code"] == "host_only_bridge_not_agent_tool"


def test_host_bridge_tools_accept_full_frontend_bridge_payload_with_host_token(monkeypatch) -> None:
    seen_requests: list[dict[str, object]] = []
    monkeypatch.setenv("VISION_MCP_HOST_BRIDGE_TOKEN", "test-host-token")
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client_frontend_bridge.kernel_list_client_frontend_events",
        lambda request: seen_requests.append(dict(request))
        or {
            "schema_version": "kernel.client_frontend_event_batch.v1",
            "cursor": str(request.get("cursor") or "0"),
            "events": [],
        },
    )

    response = call_tool(
        "kernel_list_client_frontend_events",
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "",
            "limit": 10,
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "client_a",
            "client_request_id": "req_events",
            "host_bridge_token": "test-host-token",
        },
    )

    assert response["schema_version"] == "kernel.client_frontend_event_batch.v1"
    assert response["events"] == []
    assert seen_requests
    assert "host_bridge_token" not in seen_requests[0]
