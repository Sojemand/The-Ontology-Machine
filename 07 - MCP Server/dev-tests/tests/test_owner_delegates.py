from __future__ import annotations

from mcp_server.tools import call_tool


def test_normalizer_blueprint_delegate_reaches_owner_contract() -> None:
    result = call_tool("list_default_blueprints", {})

    assert result["status"] == "ok"
    assert result["blueprints"]


def test_orchestrator_surface_delegate_reaches_owner_contract() -> None:
    result = call_tool("describe_owner_surfaces", {"module": "orchestrator"})

    assert result["status"] == "ok"
    assert result["surfaces"]

