from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server import healthcheck, permissions
from mcp_server.tools import ToolFailure, call_tool


def test_mcp_server_describe_and_read_are_limited_to_mcp_surfaces() -> None:
    described = call_tool("mcp_server.describe_surfaces", {})

    assert described["status"] == "ok"
    assert [item["surface_id"] for item in described["surfaces"]] == ["mcp_server.support_monitor"]
    assert {item["owner"] for item in described["surfaces"]} == {"mcp_server"}

    read = call_tool("mcp_server.read_surface", {"surface_id": "mcp_server.support_monitor"})
    assert read["status"] == "ok"
    assert read["surface_id"] == "mcp_server.support_monitor"
    assert "active_incident_count" in read["value"]

    with pytest.raises(ToolFailure, match="surface_id muss eines"):
        call_tool("mcp_server.read_surface", {"surface_id": "orchestrator.execution_policy"})
    with pytest.raises(ToolFailure, match="surface_id muss eines"):
        call_tool("mcp_server.read_surface", {"surface_id": "mcp_server.unknown"})


def test_mcp_server_validate_surface_rejects_read_only_support_monitor() -> None:
    with pytest.raises(ToolFailure, match="read-only"):
        call_tool("mcp_server.validate_surface", {"surface_id": "mcp_server.support_monitor", "value": {}})


def test_mcp_server_edit_tools_fail_closed_by_agent_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy_path = tmp_path / "config" / "agent_permissions.json"
    monkeypatch.setattr(permissions, "POLICY_PATH", policy_path)
    policy = permissions.default_policy()
    policy["default_agent_level"] = "L0_READONLY"
    policy["maximum_agent_level"] = "L0_READONLY"
    permissions.write_policy(policy)
    monkeypatch.setenv("VISION_MCP_AGENT_LEVEL", "L0_READONLY")

    assert call_tool("mcp_server.describe_surfaces", {})["status"] == "ok"
    assert call_tool("mcp_server.healthcheck", {})["status"] == "ok"
    with pytest.raises(ToolFailure, match="mindestens Agent-Level L3_ADMIN"):
        call_tool("mcp_server.read_surface", {"surface_id": "mcp_server.support_monitor"})
    with pytest.raises(ToolFailure, match="mindestens Agent-Level L3_ADMIN"):
        call_tool(
            "mcp_server.validate_surface",
            {"surface_id": "mcp_server.support_monitor", "value": {}},
        )


def test_mcp_server_healthcheck_reports_runtime_catalog_permissions_and_startup() -> None:
    result = call_tool("mcp_server.healthcheck", {})

    assert result["status"] == "ok"
    assert result["healthy"] is True
    assert result["transport"] == "stdio"
    assert result["network_surface"] == "none"
    assert result["runtime"]["ok"] is True
    assert result["tool_catalog"]["ok"] is True
    assert result["permission_policy"]["fail_closed"] is True
    assert result["startup"]["ok"] is True
    assert result["startup"]["network_surface"] == "none"


def test_mcp_server_healthcheck_can_enforce_strict_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    strict_flags: list[bool] = []

    def fake_runtime_check(*, strict_executable: bool = False) -> dict[str, object]:
        strict_flags.append(strict_executable)
        return {
            "ok": True,
            "missing_required_files": [],
            "errors": [],
            "strict_executable": strict_executable,
            "self_contained_runtime": True,
        }

    monkeypatch.setattr(healthcheck, "check_runtime_manifest", fake_runtime_check)

    result = call_tool("mcp_server.healthcheck", {"strict_runtime": True})

    assert result["status"] == "ok"
    assert strict_flags == [True]
    assert result["runtime"]["strict_executable"] is True
