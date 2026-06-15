"""Action and surface constants for the MCP Server edit contract."""

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"
SUPPORT_ACTIONS = (
    "assess_support_incident",
    "list_support_incidents",
    "preview_support_bug_report",
    "build_support_bug_report",
    "queue_support_bug_report",
    "dismiss_support_incident",
)

SUPPORT_MONITOR_SURFACE_ID = "mcp_server.support_monitor"

SURFACE_IDS = (SUPPORT_MONITOR_SURFACE_ID,)

__all__ = [
    "DESCRIBE_SURFACES_ACTION",
    "READ_BUNDLE_ACTION",
    "READ_SURFACE_ACTION",
    "SUPPORT_ACTIONS",
    "SUPPORT_MONITOR_SURFACE_ID",
    "SURFACE_IDS",
    "VALIDATE_SURFACE_ACTION",
    "WRITE_SURFACE_ACTION",
]
