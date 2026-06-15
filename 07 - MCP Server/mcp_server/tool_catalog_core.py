from __future__ import annotations

from typing import Any

from .edit_contract.types import SURFACE_IDS
from .tool_catalog_utils import _artifact_properties, _enum, _tool


def core_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "mcp_server.describe_surfaces",
            "List MCP Server-owned edit surfaces and metadata. This is local stdio control-plane introspection only and does not inspect foreign owner surfaces.",
            {},
        ),
        _tool(
            "mcp_server.read_surface",
            "Read exactly one MCP Server-owned surface from the local MCP edit contract. Foreign owner surfaces remain available through their dedicated owner tools.",
            {"surface_id": _enum(list(SURFACE_IDS))},
            required=("surface_id",),
        ),
        _tool(
            "mcp_server.validate_surface",
            "Validate exactly one MCP Server-owned surface without writing. The tool rejects foreign owner surfaces fail-closed.",
            {"surface_id": _enum(list(SURFACE_IDS)), "value": {"type": "object", "additionalProperties": True}},
            required=("surface_id", "value"),
        ),
        _tool(
            "mcp_server.healthcheck",
            "Check MCP Server runtime, tool catalog, permission policy and stdio start readiness without adding any network surface. Set strict_runtime to require the bundled product Python.",
            {"strict_runtime": {"type": "boolean", "default": False}},
        ),
        _tool(
            "inspect_pipeline_contract_governance",
            "Read-only governance diagnostic for MCP-visible owner modules, manifest action counts, allow-lists, edit/admin endpoints, and routing hints.",
            {},
        ),
        _tool(
            "inspect_agent_permissions",
            "Read-only inspection of the active MCP agent permission policy and fail-closed tool coverage.",
            {},
        ),
        _tool(
            "inspect_support_monitor_summary",
            "Read-only summary of local MCP support monitor state. For report work use the atomized support incident tools.",
            {},
        ),
        _tool(
            "assess_support_incident",
            "Classify a support incident before any report action. Only unexpected_exception, contract_regression, repeatable_product_failure, and data_corruption_risk may become reportable.",
            {
                "classification": {"type": "string", "enum": ["missing_path", "invalid_user_input", "missing_configuration", "expected_preflight_failure", "permission_denied", "external_dependency_failure", "unexpected_exception", "contract_regression", "repeatable_product_failure", "data_corruption_risk", "unknown"]},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"], "default": "low"},
                "incident_id": {"type": "string"},
                "event": {"type": "object", "additionalProperties": True},
                "module_key": {"type": "string"},
                "tool_action": {"type": "string"},
                "severity": {"type": "string", "enum": ["info", "warning", "error", "critical"], "default": "error"},
                "status": {"type": "string"},
                "message": {"type": "string"},
                "exception_type": {"type": "string"},
                "stacktrace": {"type": "string"},
                "redaction_class": {"type": "string", "default": "support_safe"},
                "artifact_refs": {"type": "array", "items": {}},
                "metadata": {"type": "object", "additionalProperties": True},
                "user_visible_summary": {"type": "string"},
                "evidence": {"type": "array", "items": {}},
            },
            required=("classification",),
        ),
        _tool(
            "list_support_incidents",
            "List local support incidents from MCP-owned support state.",
            {
                "show_dismissed": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "minimum": 1},
            },
        ),
        _tool(
            "preview_support_bug_report",
            "Preview a redacted local bug report for a prior reportable support assessment. Writes nothing.",
            {
                "assessment_id": {"type": "string"},
                "user_note": {"type": "string"},
                "with_recent_events": {"type": "boolean", "default": True},
            },
            required=("assessment_id",),
        ),
        _tool(
            "build_support_bug_report",
            "Build a redacted local bug report JSON file for a prior reportable support assessment.",
            {
                "assessment_id": {"type": "string"},
                "user_note": {"type": "string"},
                "with_recent_events": {"type": "boolean", "default": True},
                "output_path": {"type": "string"},
            },
            required=("assessment_id",),
        ),
        _tool(
            "queue_support_bug_report",
            "Queue one already built support bug report into the local outbox after explicit user confirmation. No network submission is attempted.",
            {
                "assessment_id": {"type": "string"},
                "report_path": {"type": "string"},
                "destination": {"type": "string", "enum": ["local_outbox"], "default": "local_outbox"},
                "user_confirmed": {"type": "boolean", "default": False},
            },
            required=("assessment_id", "report_path", "user_confirmed"),
        ),
        _tool(
            "dismiss_support_incident",
            "Dismiss one local support incident from the active list.",
            {
                "incident_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            required=("incident_id",),
        ),
        _tool(
            "describe_owner_surfaces",
            "Describe owner-local edit surfaces for Orchestrator or Normalizer.",
            {"module": _enum(["orchestrator", "normalizer"])},
            required=("module",),
        ),
        _tool(
            "read_owner_bundle",
            "Read an owner-local edit bundle.",
            {"module": _enum(["orchestrator", "normalizer"])},
            required=("module",),
        ),
        _tool(
            "read_owner_surface",
            "Read one owner-local edit surface.",
            {"module": _enum(["orchestrator", "normalizer"]), "surface_id": {"type": "string"}},
            required=("module", "surface_id"),
        ),
        _tool(
            "validate_owner_surface",
            "Validate one owner-local surface value through its owner contract.",
            {"module": _enum(["orchestrator", "normalizer"]), "surface_id": {"type": "string"}, "value": {"type": "object"}},
            required=("module", "surface_id", "value"),
        ),
        _tool(
            "write_owner_surface",
            "Write one owner-local surface through its owner contract.",
            {"module": _enum(["orchestrator", "normalizer"]), "surface_id": {"type": "string"}, "value": {"type": "object"}},
            required=("module", "surface_id", "value"),
        ),
    ]
