from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_server import tool_handlers
from mcp_server.tools import call_tool, tool_definitions


def test_validator_edit_atom_tools_are_visible_with_flat_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "validator.describe_surfaces": (set(), set()),
        "validator.read_surface": ({"surface_id"}, {"surface_id"}),
        "validator.validate_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
        "validator.write_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
    }

    assert set(expected) <= set(tools)
    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "action" not in schema["properties"]
        assert "module" not in schema["properties"]
        assert "payload" not in schema["properties"]


def test_validator_edit_atomics_delegate_exact_owner_payloads(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok", "module": module_key, "action": payload["action"]}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    call_tool("validator.describe_surfaces", {})
    call_tool("validator.read_surface", {"surface_id": "validator.settings"})
    call_tool(
        "validator.validate_surface",
        {"surface_id": "validator.report_preview_policy", "value": {"flag_needs_review": True, "max_issues_per_check": 20}},
    )
    call_tool(
        "validator.write_surface",
        {"surface_id": "validator.report_preview_policy", "value": {"flag_needs_review": False, "max_issues_per_check": 7}},
    )

    assert calls == [
        ("validator", {"action": "describe_surfaces"}),
        ("validator", {"action": "read_surface", "surface_id": "validator.settings"}),
        (
            "validator",
            {
                "action": "validate_surface",
                "surface_id": "validator.report_preview_policy",
                "value": {"flag_needs_review": True, "max_issues_per_check": 20},
            },
        ),
        (
            "validator",
            {
                "action": "write_surface",
                "surface_id": "validator.report_preview_policy",
                "value": {"flag_needs_review": False, "max_issues_per_check": 7},
            },
        ),
    ]


def test_validator_validate_surface_does_not_create_owner_home(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))

    result = call_tool(
        "validator.validate_surface",
        {"surface_id": "validator.settings", "value": _valid_settings_surface()},
    )

    assert result["status"] == "ok"
    assert not home.exists()


def test_validator_real_owner_surfaces_read_write_and_reject_invalid_payload(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))

    described = call_tool("validator.describe_surfaces", {})
    assert [surface["surface_id"] for surface in described["surfaces"]] == [
        "validator.settings",
        "validator.report_preview_policy",
        "validator.debug_capabilities",
    ]

    unknown = call_tool("validator.read_surface", {"surface_id": "validator.nope"})
    assert unknown["status"] == "error"
    assert "Unbekannte Surface" in unknown["reason"]

    current = call_tool("validator.read_surface", {"surface_id": "validator.report_preview_policy"})
    assert current["status"] == "ok"
    assert current["value"] == {"flag_needs_review": True, "max_issues_per_check": 20}

    written = call_tool(
        "validator.write_surface",
        {
            "surface_id": "validator.report_preview_policy",
            "value": {"flag_needs_review": False, "max_issues_per_check": 7},
        },
    )
    assert written["status"] == "ok"
    persisted = json.loads((home / "config" / "config.json").read_text(encoding="utf-8"))
    assert persisted["flag_needs_review"] is False
    assert persisted["max_issues_per_check"] == 7

    invalid = call_tool(
        "validator.write_surface",
        {
            "surface_id": "validator.report_preview_policy",
            "value": {"flag_needs_review": True, "max_issues_per_check": False},
        },
    )
    assert invalid["status"] == "error"
    assert "max_issues_per_check" in invalid["reason"]
    persisted_after_invalid = json.loads((home / "config" / "config.json").read_text(encoding="utf-8"))
    assert persisted_after_invalid["flag_needs_review"] is False
    assert persisted_after_invalid["max_issues_per_check"] == 7


def _valid_settings_surface() -> dict[str, Any]:
    return {
        "checks.free_text": True,
        "checks.context_scalars": True,
        "checks.content_fields": True,
        "checks.rows": True,
        "match.scalar_level": "FAIL",
        "match.row_level": "WARN",
        "match.require_free_text": True,
        "match.number_tolerance_absolute": 0.01,
        "match.min_string_length": 3,
        "match.min_compact_length": 3,
        "match.context_fields": ["supplier", "invoice_number", "invoice_date", "total_amount"],
        "match.skip_content_fields": ["notes", "description", "raw_text"],
        "match.skip_row_fields": ["_source_refs", "notes"],
        "match.row_anchor_keys": ["position", "description", "label", "item", "title", "name"],
    }
