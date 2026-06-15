"""Descriptor builders for MCP Server edit surfaces."""

from __future__ import annotations

from .types import SUPPORT_MONITOR_SURFACE_ID


def describe_surfaces(*, module_root) -> list[dict]:
    del module_root
    return [
        {
            "module_key": "mcp_server",
            "surface_id": SUPPORT_MONITOR_SURFACE_ID,
            "label": "Support Monitor",
            "kind": "capability_summary",
            "owner": "mcp_server",
            "storage_kind": "local_jsonl_state",
            "source_path": "state/support/support_events.jsonl",
            "editable": False,
            "editor_kind": "support_monitor",
            "contract_module": "mcp_server.edit_contract",
            "validation": {"mode": "read_only", "fail_closed": True},
            "preview": ["json"],
            "operation_links": [],
            "runtime_impact": "support_diagnostics_only",
            "drift_status": "runtime_state",
            "section": "Operations",
            "field_groups": [],
            "field_labels": {},
            "field_help": {},
            "render_actions_inline": False,
        },
    ]
