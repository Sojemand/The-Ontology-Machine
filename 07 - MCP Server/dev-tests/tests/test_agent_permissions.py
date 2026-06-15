from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server import permissions, tool_handlers
from mcp_server.permission_validation import required_level_for_tool
from mcp_server.protocol import handle_message
from mcp_server.semantic_control_kernel_visibility import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)
from mcp_server.tools import ToolFailure, call_tool, tool_definitions
from tests.agent_permissions_contract_support import copy_module, expected_visible_names, invoke_contract


def _all_tool_names() -> set[str]:
    return {str(tool["name"]) for tool in tool_definitions()}


def _isolated_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    policy_path = tmp_path / "config" / "agent_permissions.json"
    monkeypatch.setattr(permissions, "POLICY_PATH", policy_path)
    for name in ("VISION_MCP_AGENT_LEVEL", "MCP_AGENT_LEVEL"):
        monkeypatch.delenv(name, raising=False)
    return policy_path


def test_default_agent_policy_covers_every_visible_tool() -> None:
    policy = permissions.validate_policy(permissions.default_policy())
    configured = permissions.configured_tools(policy)

    assert policy["default_agent_level"] == "L1_AUTHOR"
    assert permissions.tools_for_level(policy, "L3_ADMIN") == _all_tool_names()
    assert sorted(_all_tool_names() - configured) == []


def test_agent_level_blocks_tools_before_owner_contract_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _isolated_policy(tmp_path, monkeypatch)
    policy = permissions.default_policy()
    policy["default_agent_level"] = "L0_READONLY"
    policy["maximum_agent_level"] = "L0_READONLY"
    permissions.write_policy(policy)

    calls: list[tuple[str, dict]] = []

    def fake_admin(module_key: str, payload: dict) -> dict:
        calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_admin", fake_admin)

    readonly = call_tool("inspect_agent_permissions", {})
    assert readonly["agent_permissions"]["active_agent_level"] == "L0_READONLY"

    with pytest.raises(ToolFailure, match="mindestens Agent-Level L3_ADMIN"):
        call_tool("inspect_runtime_credentials", {})

    assert calls == []


def test_tools_list_only_exposes_active_level_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _isolated_policy(tmp_path, monkeypatch)
    policy = permissions.default_policy()
    policy["default_agent_level"] = "L2_OPERATOR"
    policy["maximum_agent_level"] = "L3_ADMIN"
    permissions.write_policy(policy)
    monkeypatch.setenv("VISION_MCP_AGENT_LEVEL", "L2_OPERATOR")

    response = handle_message({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})

    assert response is not None
    listed = {str(tool["name"]) for tool in response["result"]["tools"]}
    expected = expected_visible_names(policy, "L2_OPERATOR")
    assert listed == expected
    assert set(PERMANENT_AGENT_TOOL_NAMES) <= listed
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(listed)
    assert set(EVENT_SCOPED_RECOVERY_TOOL_NAMES).isdisjoint(listed)
    assert set(KERNEL_INTERNAL_TOOL_NAMES).isdisjoint(listed)
    assert set(KERNEL_CONTINUATION_TOOL_NAMES).isdisjoint(listed)
    admin_tools = {"mcp_server.read_surface", "mcp_server.validate_surface", "read_runtime_settings", "write_runtime_settings", "reset_runtime_settings", "inspect_runtime_credentials", "set_runtime_api_key", "delete_runtime_api_key", "reveal_secret"}
    assert admin_tools.isdisjoint(listed)
    assert {"generate_embeddings", "activate_corpus_context"}.issubset(expected_visible_names(policy, "L2_OPERATOR"))


def test_working_release_package_tool_is_operator_only_in_policy() -> None:
    policy = permissions.validate_policy(permissions.default_policy())

    expected = {
        "create_working_release_package": "L2_OPERATOR",
        "read_translation_glossary": "L1_AUTHOR",
        "upsert_translation_glossary_entry": "L2_OPERATOR",
        "remove_translation_glossary_entry": "L2_OPERATOR",
    }
    assert {tool: required_level_for_tool(policy, tool) for tool in expected} == expected


def test_semantic_control_kernel_surface_is_inherited_at_every_agent_level() -> None:
    policy = permissions.validate_policy(permissions.default_policy())
    expected = set(PERMANENT_AGENT_TOOL_NAMES)

    for level in policy["level_order"]:
        assert permissions.tools_for_level(policy, level) & expected == expected


def test_agent_level_environment_cannot_exceed_policy_ceiling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _isolated_policy(tmp_path, monkeypatch)
    policy = permissions.default_policy()
    policy["default_agent_level"] = "L0_READONLY"
    policy["maximum_agent_level"] = "L0_READONLY"
    permissions.write_policy(policy)
    monkeypatch.setenv("VISION_MCP_AGENT_LEVEL", "L3_ADMIN")

    with pytest.raises(ToolFailure, match="ueberschreitet maximum_agent_level"):
        call_tool("inspect_agent_permissions", {})


def test_mcp_server_edit_contract_exposes_support_monitor_only(tmp_path: Path) -> None:
    module_root = copy_module(tmp_path)

    described = invoke_contract(module_root, {"action": "describe_surfaces"})
    assert described["status"] == "ok"
    assert "MCP SERVER PERMISSION SUMMARY" in described["module_summary"]
    labels = [card["label"] for card in described["summary_cards"]]
    assert labels == ["Module Role", "Support Monitor"]
    assert [item["surface_id"] for item in described["surfaces"]] == ["mcp_server.support_monitor"]
    assert described["surfaces"][0]["editable"] is False
    assert described["surfaces"][0]["editor_kind"] == "support_monitor"

    bundle = invoke_contract(module_root, {"action": "read_bundle"})
    assert bundle["status"] == "ok"
    support = bundle["surfaces"][0]["value"]
    assert "active_incident_count" in support


def test_mcp_server_edit_contract_rejects_removed_agent_permissions_surface(tmp_path: Path) -> None:
    module_root = copy_module(tmp_path)

    response = invoke_contract(
        module_root,
        {
            "action": "read_surface",
            "surface_id": "mcp_server.agent_permissions",
        },
    )

    assert response["status"] == "error"
    assert "Unbekannte Surface" in response["reason"]
