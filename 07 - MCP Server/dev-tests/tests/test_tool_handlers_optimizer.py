from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions


def test_optimizer_atomic_tools_are_visible_with_flat_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "optimizer.classify_document": ({"source_path", "input_root", "timeout_seconds"}, {"source_path", "input_root"}),
        "optimizer.extract_document": (
            {
                "source_path",
                "input_root",
                "output_root",
                "raw_output_path",
                "page_images_dir",
                "logical_source_path",
                "optimizer_profile",
                "runtime_policy_path",
                "timeout_seconds",
            },
            {
                "source_path",
                "input_root",
                "output_root",
                "raw_output_path",
                "page_images_dir",
                "logical_source_path",
                "optimizer_profile",
            },
        ),
        "optimizer.healthcheck": ({"optimizer_profile", "scope", "required_dependencies", "timeout_seconds"}, set()),
        "optimizer.scan_debug_input": (
            {
                "input_root",
                "debug_root",
                "session_root",
                "optimizer_profile",
                "filters",
                "hash_tools",
                "timeout_seconds",
            },
            {"input_root", "debug_root", "session_root"},
        ),
        "optimizer.describe_surfaces": (set(), set()),
        "optimizer.read_surface": ({"surface_id"}, {"surface_id"}),
        "optimizer.validate_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
        "optimizer.write_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
    }

    assert set(expected) <= set(tools)
    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "action" not in schema["properties"]
        assert "payload" not in schema["properties"]


def test_optimizer_edit_surface_tools_delegate_to_owner_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        if payload.get("action") == "describe_surfaces":
            return {
                "status": "ok",
                "surfaces": [
                    {"surface_id": "optimizer.settings"},
                    {"surface_id": "optimizer.signature_rules"},
                    {"surface_id": "optimizer.signature_overrides"},
                    {"surface_id": "optimizer.debug_capabilities"},
                ],
            }
        return {"status": "ok", "surface_id": payload.get("surface_id"), "value": payload.get("value")}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    described = call_tool("optimizer.describe_surfaces", {})
    assert [item["surface_id"] for item in described["surfaces"]] == [
        "optimizer.settings",
        "optimizer.signature_rules",
        "optimizer.signature_overrides",
        "optimizer.debug_capabilities",
    ]
    assert call_tool("optimizer.read_surface", {"surface_id": "optimizer.settings"})["status"] == "ok"
    assert (
        call_tool(
            "optimizer.validate_surface",
            {"surface_id": "optimizer.signature_overrides", "value": {"version": 1, "overrides": {}}},
        )["status"]
        == "ok"
    )
    assert (
        call_tool(
            "optimizer.write_surface",
            {"surface_id": "optimizer.signature_overrides", "value": {"version": 1, "overrides": {}}},
        )["status"]
        == "ok"
    )

    assert calls == [
        ("optimizer", {"action": "describe_surfaces"}, {}),
        ("optimizer", {"action": "read_surface", "surface_id": "optimizer.settings"}, {}),
        (
            "optimizer",
            {
                "action": "validate_surface",
                "surface_id": "optimizer.signature_overrides",
                "value": {"version": 1, "overrides": {}},
            },
            {},
        ),
        (
            "optimizer",
            {
                "action": "write_surface",
                "surface_id": "optimizer.signature_overrides",
                "value": {"version": 1, "overrides": {}},
            },
            {},
        ),
    ]


def test_optimizer_validate_surface_does_not_call_write(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_invoke(_module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append(payload)
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool(
        "optimizer.validate_surface",
        {"surface_id": "optimizer.signature_overrides", "value": {"version": 1, "overrides": {}}},
    )

    assert result["status"] == "ok"
    assert calls == [
        {
            "action": "validate_surface",
            "surface_id": "optimizer.signature_overrides",
            "value": {"version": 1, "overrides": {}},
        }
    ]


def test_optimizer_edit_surface_unknown_id_fails_closed_in_owner_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_invoke(_module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append(payload)
        return {"status": "error", "reason": f"Unbekannte Surface: {payload.get('surface_id')}"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool("optimizer.read_surface", {"surface_id": "optimizer.missing"})

    assert result["status"] == "error"
    assert result["reason"] == "Unbekannte Surface: optimizer.missing"
    assert calls == [{"action": "read_surface", "surface_id": "optimizer.missing"}]
