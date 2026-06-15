from __future__ import annotations

from mcp_server.permissions import visible_tool_definitions
from mcp_server.semantic_control_kernel_visibility import (
    EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_NAMES,
    KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES,
)
from mcp_server.tool_catalog import tool_definitions


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def _schema_for(name: str) -> dict[str, object]:
    if name == "kernel_continue_resumable_workflow":
        return {
            "type": "object",
            "properties": {"resume_option_ref": {"type": "string"}},
            "required": ["resume_option_ref"],
            "additionalProperties": False,
        }
    return _empty_schema()


def test_catalog_snapshot_matches_phase16_permanent_semantic_control_kernel_surface(monkeypatch) -> None:
    def fake_list(_self, scope: str) -> dict[str, object]:
        assert scope == "permanent_agent"
        return {
            "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
            "scope": scope,
            "tool_definitions": [
                {"name": name, "description": name, "inputSchema": _schema_for(name)}
                for name in PERMANENT_AGENT_TOOL_NAMES
            ],
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        fake_list,
    )

    catalog_names = [str(tool["name"]) for tool in tool_definitions()]
    visible_names = [str(tool["name"]) for tool in visible_tool_definitions()]

    kernel_catalog_names = [name for name in catalog_names if name in set(PERMANENT_AGENT_TOOL_NAMES)]
    kernel_visible_names = [name for name in visible_names if name in set(PERMANENT_AGENT_TOOL_NAMES)]

    assert kernel_catalog_names == list(PERMANENT_AGENT_TOOL_NAMES)
    assert kernel_visible_names == list(PERMANENT_AGENT_TOOL_NAMES)
    assert len(kernel_catalog_names) == len(PERMANENT_AGENT_TOOL_NAMES)
    assert set(EVENT_SCOPED_RECOVERY_TOOL_NAMES).isdisjoint(catalog_names)
    assert set(KERNEL_INTERNAL_TOOL_NAMES).isdisjoint(catalog_names)
    assert set(KERNEL_CONTINUATION_TOOL_NAMES).isdisjoint(catalog_names)
    assert set(HOST_ONLY_CLIENT_BRIDGE_NAMES).isdisjoint(catalog_names)
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(catalog_names)
