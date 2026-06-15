from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

from mcp_server.orchestrator_contract import main as contract_main
from mcp_server.protocol import handle_message


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def test_top_level_modules_start_without_legacy_kernel_imports(monkeypatch, tmp_path: Path) -> None:
    from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES

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

    importlib.import_module("mcp_server.protocol")
    importlib.import_module("mcp_server.server")
    importlib.import_module("mcp_server.tool_catalog")
    importlib.import_module("mcp_server.tool_handlers")
    importlib.import_module("mcp_server.tool_handler_registry")

    response = handle_message({"jsonrpc": "2.0", "id": "list", "method": "tools/list", "params": {}})
    names = [tool["name"] for tool in response["result"]["tools"]]
    kernel_names = [name for name in names if name in set(PERMANENT_AGENT_TOOL_NAMES)]
    assert kernel_names == list(PERMANENT_AGENT_TOOL_NAMES)
    assert "llm_action_catalog" not in names
    assert "open_workflow" not in names

    response_path = tmp_path / "healthcheck.json"
    assert contract_main(["--response", str(response_path)]) == 0
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"


def test_deleted_legacy_modules_are_not_importable() -> None:
    assert importlib.util.find_spec("mcp_server.semantic_kernel") is None
    assert importlib.util.find_spec("mcp_server.tool_catalog_semantic_kernel") is None
    assert importlib.util.find_spec("mcp_server.tool_handlers_semantic_kernel") is None
