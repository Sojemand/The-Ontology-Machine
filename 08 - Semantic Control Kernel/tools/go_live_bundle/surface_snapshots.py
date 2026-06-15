from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_DEFINITIONS
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS

from .paths import CLIENT_FRONTEND_ROOT, MCP_SERVER_ROOT, MODULE_ROOT, _json_file, _mkdir, _write_json


def _live_tool_surface_contracts() -> dict[str, Any]:
    if str(MCP_SERVER_ROOT) not in sys.path:
        sys.path.insert(0, str(MCP_SERVER_ROOT))
    from mcp_server.semantic_control_kernel_visibility import (
        EVENT_SCOPED_RECOVERY_TOOL_NAMES as mcp_event_scoped_tool_names,
        EVENT_SCOPED_TOOL_SCOPE_FIELDS,
        HOST_ONLY_CLIENT_BRIDGE_NAMES as mcp_host_only_client_bridge_names,
        KERNEL_CONTINUATION_SCOPE_FIELDS,
        KERNEL_CONTINUATION_TOOL_NAMES as mcp_continuation_tool_names,
        KERNEL_INTERNAL_SCOPE_FIELDS,
        KERNEL_INTERNAL_TOOL_NAMES as mcp_kernel_internal_tool_names,
        LEGACY_RETIRED_TOOL_NAMES as mcp_legacy_retired_tool_names,
        PERMANENT_AGENT_TOOL_NAMES as mcp_permanent_tool_names,
    )
    from mcp_server.tool_catalog_semantic_control_kernel import semantic_control_kernel_tools

    frontend_kernel_client = CLIENT_FRONTEND_ROOT / "client_frontend" / "pipeline_agent" / "kernel_client.js"
    frontend_permanent_tool_names = _read_frontend_exported_string_list(frontend_kernel_client, "PERMANENT_AGENT_TOOL_NAMES")
    frontend_event_scoped_tool_names = _read_frontend_exported_string_list(frontend_kernel_client, "EVENT_SCOPED_RECOVERY_TOOL_NAMES")
    kernel_permanent_tool_names = [definition.tool_name for definition in PERMANENT_AGENT_TOOL_DEFINITIONS]
    kernel_event_scoped_tool_names = [definition.tool_name for definition in EVENT_SCOPED_RECOVERY_TOOL_DEFINITIONS]
    public_tool_definitions = list(semantic_control_kernel_tools())
    public_tool_names = [str(tool.get("name") or "") for tool in public_tool_definitions]
    return {
        "public_tool_definitions": public_tool_definitions,
        "public_tool_names": public_tool_names,
        "mcp_permanent_tool_names": list(mcp_permanent_tool_names),
        "mcp_event_scoped_tool_names": list(mcp_event_scoped_tool_names),
        "mcp_kernel_internal_tool_names": list(mcp_kernel_internal_tool_names),
        "mcp_continuation_tool_names": list(mcp_continuation_tool_names),
        "mcp_host_only_client_bridge_names": list(mcp_host_only_client_bridge_names),
        "mcp_legacy_retired_tool_names": list(mcp_legacy_retired_tool_names),
        "mcp_kernel_internal_scope_fields": list(KERNEL_INTERNAL_SCOPE_FIELDS),
        "mcp_continuation_scope_fields": list(KERNEL_CONTINUATION_SCOPE_FIELDS),
        "mcp_event_scoped_scope_fields": {name: list(fields) for name, fields in EVENT_SCOPED_TOOL_SCOPE_FIELDS.items()},
        "frontend_permanent_tool_names": frontend_permanent_tool_names,
        "frontend_event_scoped_tool_names": frontend_event_scoped_tool_names,
        "kernel_permanent_tool_names": kernel_permanent_tool_names,
        "kernel_event_scoped_tool_names": kernel_event_scoped_tool_names,
        "parity": {
            "public_matches_mcp_visibility": public_tool_names == list(mcp_permanent_tool_names),
            "mcp_matches_frontend_permanent_surface": list(mcp_permanent_tool_names) == frontend_permanent_tool_names,
            "mcp_matches_kernel_permanent_surface": list(mcp_permanent_tool_names) == kernel_permanent_tool_names,
            "mcp_matches_frontend_recovery_surface": list(mcp_event_scoped_tool_names) == frontend_event_scoped_tool_names,
            "mcp_matches_kernel_recovery_surface": list(mcp_event_scoped_tool_names) == kernel_event_scoped_tool_names,
        },
    }


def _read_frontend_exported_string_list(path: Path, export_name: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"export const {re.escape(export_name)} = \[(.*?)\];", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Could not find {export_name} in {path}")
    return re.findall(r'"([^"]+)"', match.group(1))


def _write_tool_snapshots(
    bundle_root: Path,
    run_id: str,
    *,
    contracts_loader: Callable[[], dict[str, Any]] | None = None,
) -> None:
    empty_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    _mkdir(bundle_root / "snapshots")
    contracts = (contracts_loader or _live_tool_surface_contracts)()
    public_tools = []
    for definition in contracts["public_tool_definitions"]:
        public_tools.append(
            {
                "name": str(definition.get("name") or ""),
                "description": str(definition.get("description") or ""),
                "inputSchema": dict(definition.get("inputSchema") or empty_schema),
            }
        )
    _write_json(
        bundle_root / "mcp_public_agent_snapshot.json",
        {
            "schema_version": "semantic_control_kernel.phase20.mcp_public_agent_snapshot.v1",
            "go_live_run_id": run_id,
            "scope": "permanent_agent",
            "tool_definitions": public_tools,
            "tool_name_parity": dict(contracts["parity"]),
            "source_contracts": {
                "mcp_permanent_tool_names": list(contracts["mcp_permanent_tool_names"]),
                "frontend_permanent_tool_names": list(contracts["frontend_permanent_tool_names"]),
                "kernel_permanent_tool_names": list(contracts["kernel_permanent_tool_names"]),
            },
        },
    )
    _write_json(
        bundle_root / "agent_tool_list_snapshot.json",
        {
            "schema_version": "semantic_control_kernel.phase20.agent_tool_list_snapshot.v1",
            "go_live_run_id": run_id,
            "model_visible_schema": empty_schema,
            "frontend_permanent_tool_names": list(contracts["frontend_permanent_tool_names"]),
            "tools": [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": empty_schema,
                }
                for tool in public_tools
            ],
        },
    )
    _write_json(
        bundle_root / "mcp_kernel_internal_contract_snapshot.json",
        {
            "schema_version": "semantic_control_kernel.phase20.mcp_kernel_internal_contract_snapshot.v1",
            "go_live_run_id": run_id,
            "permanent_agent_tools": list(contracts["mcp_permanent_tool_names"]),
            "event_scoped_recovery_tools": list(contracts["mcp_event_scoped_tool_names"]),
            "kernel_internal_tools": list(contracts["mcp_kernel_internal_tool_names"]),
            "continuation_scoped_tools": list(contracts["mcp_continuation_tool_names"]),
            "host_only_client_frontend_bridge_tools": list(contracts["mcp_host_only_client_bridge_names"]),
            "legacy_retired_names": list(contracts["mcp_legacy_retired_tool_names"]),
            "kernel_internal_scope_fields": list(contracts["mcp_kernel_internal_scope_fields"]),
            "event_scoped_scope_fields": dict(contracts["mcp_event_scoped_scope_fields"]),
            "tool_name_parity": dict(contracts["parity"]),
            "bridge_entrypoint": "python -m semantic_control_kernel.orchestrator_contract",
        },
    )
    _write_json(
        bundle_root / "mcp_continuation_scope_snapshot.json",
        {
            "schema_version": "semantic_control_kernel.phase20.mcp_continuation_scope_snapshot.v1",
            "go_live_run_id": run_id,
            "operation_names": list(contracts["mcp_continuation_tool_names"]),
            "classification": "removed",
            "required_hidden_fields": list(contracts["mcp_continuation_scope_fields"]),
            "absent_from_public_agent_surface": True,
            "absent_from_event_scoped_recovery_surface": True,
            "absent_from_kernel_internal_surface": True,
            "absent_from_host_only_client_bridge_surface": True,
        },
    )
    (bundle_root / "snapshots" / "README.md").write_text(
        "# Snapshots\n\nPublic and internal surface snapshots for the Phase 20 go-live bundle.\n",
        encoding="utf-8",
    )


def _write_runtime_snapshot(bundle_root: Path, run_id: str) -> None:
    module_manifest = _json_file(MODULE_ROOT / "module-manifest.json")
    runtime_manifest = _json_file(MODULE_ROOT / "runtime" / "runtime-manifest.json")
    _write_json(
        bundle_root / "runtime_manifest_snapshot.json",
        {
            "schema_version": "semantic_control_kernel.phase20.runtime_manifest_snapshot.v1",
            "go_live_run_id": run_id,
            "module_manifest": module_manifest,
            "runtime_manifest": runtime_manifest,
            "status_contract_consistent": module_manifest.get("status") == runtime_manifest.get("status"),
            "contract_version_consistent": module_manifest.get("contract_version") == runtime_manifest.get("contract_version"),
        },
    )
