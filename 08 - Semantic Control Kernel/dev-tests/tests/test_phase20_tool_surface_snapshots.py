from __future__ import annotations

import re
import sys
from pathlib import Path

from phase20_go_live_support import latest_go_live_dir, load_json


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
MCP_SERVER_ROOT = PIPELINE_ROOT / "07 - MCP Server"
FRONTEND_KERNEL_CLIENT = PIPELINE_ROOT / "Client Frontend" / "client_frontend" / "pipeline_agent" / "kernel_client.js"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(MCP_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_ROOT))

from mcp_server.semantic_control_kernel_visibility import (  # noqa: E402
    EVENT_SCOPED_RECOVERY_TOOL_NAMES as MCP_EVENT_SCOPED_RECOVERY_TOOL_NAMES,
    HOST_ONLY_CLIENT_BRIDGE_NAMES as MCP_HOST_ONLY_CLIENT_BRIDGE_NAMES,
    KERNEL_CONTINUATION_SCOPE_FIELDS,
    KERNEL_CONTINUATION_TOOL_NAMES as MCP_KERNEL_CONTINUATION_TOOL_NAMES,
    KERNEL_INTERNAL_SCOPE_FIELDS,
    KERNEL_INTERNAL_TOOL_NAMES as MCP_KERNEL_INTERNAL_TOOL_NAMES,
    LEGACY_RETIRED_TOOL_NAMES as MCP_LEGACY_RETIRED_TOOL_NAMES,
    PERMANENT_AGENT_TOOL_NAMES as MCP_PERMANENT_AGENT_TOOL_NAMES,
)
from mcp_server.tool_catalog_semantic_control_kernel import semantic_control_kernel_tools  # noqa: E402
from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_DEFINITIONS  # noqa: E402
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS  # noqa: E402


def _read_frontend_exported_string_list(export_name: str) -> list[str]:
    text = FRONTEND_KERNEL_CLIENT.read_text(encoding="utf-8")
    match = re.search(rf"export const {re.escape(export_name)} = \[(.*?)\];", text, re.DOTALL)
    assert match is not None
    return re.findall(r'"([^"]+)"', match.group(1))


def test_public_snapshot_contains_exactly_the_permanent_tools() -> None:
    payload = load_json(latest_go_live_dir() / "mcp_public_agent_snapshot.json")
    expected = [str(tool["name"]) for tool in semantic_control_kernel_tools()]
    actual = [item["name"] for item in payload["tool_definitions"]]

    assert actual == expected
    assert actual == list(MCP_PERMANENT_AGENT_TOOL_NAMES)
    assert actual == _read_frontend_exported_string_list("PERMANENT_AGENT_TOOL_NAMES")
    assert actual == [definition.tool_name for definition in PERMANENT_AGENT_TOOL_DEFINITIONS]
    assert len(actual) == 16
    assert payload["tool_name_parity"]["public_matches_mcp_visibility"] is True
    assert payload["tool_name_parity"]["mcp_matches_frontend_permanent_surface"] is True
    assert payload["tool_name_parity"]["mcp_matches_kernel_permanent_surface"] is True


def test_internal_snapshot_separates_public_recovery_internal_and_continuation_names() -> None:
    root = latest_go_live_dir()
    internal = load_json(root / "mcp_kernel_internal_contract_snapshot.json")
    continuation = load_json(root / "mcp_continuation_scope_snapshot.json")
    expected_recovery = list(MCP_EVENT_SCOPED_RECOVERY_TOOL_NAMES)

    assert internal["event_scoped_recovery_tools"] == expected_recovery
    assert expected_recovery == _read_frontend_exported_string_list("EVENT_SCOPED_RECOVERY_TOOL_NAMES")
    assert expected_recovery == [definition.tool_name for definition in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS]
    assert internal["kernel_internal_tools"] == list(MCP_KERNEL_INTERNAL_TOOL_NAMES)
    assert internal["continuation_scoped_tools"] == list(MCP_KERNEL_CONTINUATION_TOOL_NAMES)
    assert internal["host_only_client_frontend_bridge_tools"] == list(MCP_HOST_ONLY_CLIENT_BRIDGE_NAMES)
    assert internal["legacy_retired_names"] == list(MCP_LEGACY_RETIRED_TOOL_NAMES)
    assert internal["kernel_internal_scope_fields"] == list(KERNEL_INTERNAL_SCOPE_FIELDS)
    assert internal["tool_name_parity"]["mcp_matches_frontend_recovery_surface"] is True
    assert internal["tool_name_parity"]["mcp_matches_kernel_recovery_surface"] is True
    assert continuation["operation_names"] == []
    assert continuation["classification"] == "removed"
    assert continuation["required_hidden_fields"] == list(KERNEL_CONTINUATION_SCOPE_FIELDS)
    assert continuation["absent_from_public_agent_surface"] is True
    assert continuation["absent_from_event_scoped_recovery_surface"] is True
    assert continuation["absent_from_kernel_internal_surface"] is True
    assert continuation["absent_from_host_only_client_bridge_surface"] is True


def test_agent_tool_list_snapshot_uses_empty_model_visible_schema() -> None:
    payload = load_json(latest_go_live_dir() / "agent_tool_list_snapshot.json")
    expected_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    expected_frontend_names = _read_frontend_exported_string_list("PERMANENT_AGENT_TOOL_NAMES")

    assert payload["model_visible_schema"] == expected_schema
    assert payload["frontend_permanent_tool_names"] == expected_frontend_names
    for tool in payload["tools"]:
        assert tool["inputSchema"] == expected_schema


def test_client_frontend_event_snapshot_is_runtime_sourced() -> None:
    payload = load_json(latest_go_live_dir() / "client_frontend_event_snapshot.json")
    kinds = {event["frontend_event_kind"] for event in payload["events"]}
    mirror_events = [
        event["mirror_event"]
        for event in payload["events"]
        if event["frontend_event_kind"] == "mirror_event"
    ]

    assert payload["source_contract"] == "kernel_list_client_frontend_events"
    assert payload["source_event_refs"]["interaction_request_refs"]
    assert payload["source_event_refs"]["progress_event_refs"]
    assert payload["source_event_refs"]["mirror_event_refs"]
    assert payload["source_event_refs"]["tool_availability_refs"]
    assert {"interaction_request", "progress_event", "mirror_event", "tool_availability"} <= kinds
    assert any(
        mirror["event_type"] == "llm_validation_failed_final"
        and str(mirror["support_bundle_ref"]["support_bundle_path"]).startswith("support/bundles/")
        for mirror in mirror_events
    )
