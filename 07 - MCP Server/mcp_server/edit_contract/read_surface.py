"""Read operations for MCP Server edit-contract surfaces."""

from __future__ import annotations

from ..support_monitor import support_surface_value
from .types import SUPPORT_MONITOR_SURFACE_ID


def read_surface(surface_id: str, *, module_root) -> dict:
    del module_root
    if surface_id == SUPPORT_MONITOR_SURFACE_ID:
        return support_surface_value()
    raise ValueError(f"Unbekannte Surface: {surface_id}")
