from __future__ import annotations

from mcp_server.semantic_control_kernel_visibility import LEGACY_RETIRED_TOOL_NAMES, PERMANENT_AGENT_TOOL_NAMES
from mcp_server.tool_catalog import tool_definitions
from mcp_server.tool_handler_registry import handlers


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def test_registry_and_catalog_are_unlinked_from_old_kernel_names(monkeypatch) -> None:
    def fake_list(_self, scope: str) -> dict[str, object]:
        assert scope == "permanent_agent"
        return {
            "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
            "scope": scope,
            "tool_definitions": [
                {"name": name, "description": name, "inputSchema": _empty_schema()}
                for name in PERMANENT_AGENT_TOOL_NAMES
            ],
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        fake_list,
    )

    registry_names = set(handlers())
    catalog_names = {str(tool["name"]) for tool in tool_definitions()}

    assert set(PERMANENT_AGENT_TOOL_NAMES) <= registry_names
    assert set(PERMANENT_AGENT_TOOL_NAMES) <= catalog_names
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(registry_names)
    assert set(LEGACY_RETIRED_TOOL_NAMES).isdisjoint(catalog_names)
    assert "reingest_pipeline_batch" not in registry_names
    assert "reingest_pipeline_batch" not in catalog_names
