from __future__ import annotations

from mcp_server.tool_catalog import tool_definitions
from mcp_server.tools import call_tool


FORBIDDEN_KEYS = {
    "workflow_catalog_summary",
    "safe_next_kernel_workflows",
    "recommended_first_workflow_family_id",
    "related_workflow_family_ids",
    "first_workflow_family_id",
    "workflow_family_id",
}


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def test_product_semantics_outputs_only_canonical_kernel_and_mcp_tool_names(monkeypatch) -> None:
    def fake_list(_self, scope: str) -> dict[str, object]:
        from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES

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

    explain = call_tool("explain_pipeline_capabilities", {"question": "Was kann ich mit der Datenbank tun?"})
    context = call_tool("inspect_pipeline_product_context", {"max_workflows": 40})
    recommend = call_tool("recommend_pipeline_next_steps", {"goal": "Die Suche findet nicht das Erwartete."})
    known_names = {str(tool["name"]) for tool in tool_definitions()}

    assert _forbidden_keys(explain) == set()
    assert _forbidden_keys(context) == set()
    assert _forbidden_keys(recommend) == set()
    assert set(explain["safe_next_kernel_tools"]) <= known_names
    assert set(explain["safe_next_mcp_tools"]) <= known_names
    assert set(context["safe_next_kernel_tools"]) <= known_names
    assert set(context["safe_next_mcp_tools"]) <= known_names
    assert set(recommend["safe_next_kernel_tools"]) <= known_names
    assert set(recommend["safe_next_mcp_tools"]) <= known_names
    assert "empty_database_default_taxonomy_no_projections" in explain["safe_next_kernel_tools"]
    assert recommend["recommended_path"]["first_mcp_tool"] == "search_corpus"
    assert recommend["recommended_path"]["first_kernel_tool"] is None
    assert "search_corpus" in recommend["safe_next_mcp_tools"]
    assert "create_custom_taxonomy_path" in recommend["safe_next_kernel_tools"]
    assert any(
        "empty_database_default_taxonomy_no_projections" in group["kernel_tool_names"]
        for group in explain["capability_groups"]
    )
    assert any(
        item["tool_name"] == "empty_database_default_taxonomy_no_projections"
        for item in context["kernel_tool_summary"]["items"]
    )


def _forbidden_keys(payload: object) -> set[str]:
    seen: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key) in FORBIDDEN_KEYS:
                    seen.add(str(key))
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return seen
