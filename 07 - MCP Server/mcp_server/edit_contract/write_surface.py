"""Write operations for MCP Server edit-contract surfaces."""

from __future__ import annotations

from .types import SUPPORT_MONITOR_SURFACE_ID


def write_surface(surface_id: str, value: dict, *, module_root) -> dict:
    del module_root, value
    if surface_id == SUPPORT_MONITOR_SURFACE_ID:
        raise ValueError("mcp_server.support_monitor ist read-only.")
    raise ValueError(f"Unbekannte Surface: {surface_id}")
