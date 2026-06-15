from __future__ import annotations

from io import BytesIO

from mcp_server import permissions
from mcp_server.protocol import encode_framed_message, handle_message, read_framed_message
from mcp_server.semantic_control_kernel_visibility import LEGACY_RETIRED_TOOL_NAMES


def test_framed_message_round_trip() -> None:
    message = {"jsonrpc": "2.0", "id": 1, "method": "ping"}

    decoded = read_framed_message(BytesIO(encode_framed_message(message)))

    assert decoded == message


def test_protocol_lists_tools(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(permissions, "POLICY_PATH", tmp_path / "config" / "agent_permissions.json")
    permissions.write_policy(permissions.default_policy())
    monkeypatch.setenv("VISION_MCP_AGENT_LEVEL", "L3_ADMIN")

    response = handle_message({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})

    assert response is not None
    assert response["id"] == 7
    listed = {tool["name"] for tool in response["result"]["tools"]}
    assert "empty_database_default_taxonomy_default_projections" in listed
    assert "empty_database_default_taxonomy_no_projections" in listed
    assert "kernel_status" in listed
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(listed)
    assert "kernel_open_recovery_dialog" not in listed


def test_unknown_tool_call_returns_mcp_error_result() -> None:
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "unknown_blocked_capability", "arguments": {}},
        }
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert "Unbekanntes Tool" in response["result"]["content"][0]["text"]
