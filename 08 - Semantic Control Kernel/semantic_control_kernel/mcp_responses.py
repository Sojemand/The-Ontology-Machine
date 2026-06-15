from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.mcp_recovery_response_text import (
    recovery_applied_summary,
    recovery_rejected_summary,
    recovery_support_only_summary,
)
from semantic_control_kernel.surface.mcp_tool_schemas import PERMANENT_AGENT_TOOL_NAMES
from semantic_control_kernel.types.mcp import MCP_RESPONSE_SCHEMA_VERSION
from semantic_control_kernel.validation.mcp_validation import validate_mcp_response_envelope


def agent_result_response(tool_name: str, result: Mapping[str, Any]) -> dict[str, Any]:
    result_status = str(result.get("status") or "")
    effect = str(result.get("effect") or "none")
    if result_status == "blocked":
        status = "blocked"
    elif result_status == "rejected":
        status = "rejected"
    elif effect == "workflow_started":
        status = "accepted"
    else:
        status = "completed"
    payload = {
        "schema_version": MCP_RESPONSE_SCHEMA_VERSION,
        "status": status,
        "tool_name": tool_name,
        "effect": effect,
        "user_visible_summary": str(result.get("user_visible_summary") or "The Kernel completed the support/control request."),
        "mirror_event": result.get("mirror_event"),
        "error": None,
    }
    if result.get("workflow_run_id"):
        payload["workflow_run_id"] = str(result["workflow_run_id"])
    for field_name in ("resume_state", "active_state", "implemented_by_phase"):
        value = result.get(field_name)
        if value is not None:
            payload[field_name] = copy_value(value)
    if result.get("error") is not None:
        result_error = dict(result["error"])
        payload["error"] = {
            "code": str(result_error.get("code") or "kernel_tool_rejected"),
            "category": "contract_validation",
            "safe_message": str(result_error.get("message") or payload["user_visible_summary"]),
        }
        for key, value in result_error.items():
            if key in {"code", "message"} or value is None:
                continue
            payload["error"][key] = copy_value(value)
    payload.update(
        extra_fields(
            result,
            exclude={
                "schema_version",
                "tool_name",
                "status",
                "effect",
                "user_visible_summary",
                "workflow_run_id",
                "mirror_event",
                "resume_state",
                "active_state",
                "implemented_by_phase",
                "error",
            },
        )
    )
    validate_mcp_response_envelope(payload)
    return payload


def accepted_response(
    tool_name: str,
    *,
    effect: str,
    summary: str,
    workflow_run_id: str | None = None,
    mirror_event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": MCP_RESPONSE_SCHEMA_VERSION,
        "status": "accepted",
        "tool_name": tool_name,
        "effect": effect,
        "user_visible_summary": summary,
        "mirror_event": dict(mirror_event) if isinstance(mirror_event, Mapping) else None,
        "error": None,
    }
    if workflow_run_id:
        payload["workflow_run_id"] = workflow_run_id
    return payload


def failure_response(
    tool_name: str,
    *,
    code: str,
    category: str,
    safe_message: str,
    status: str = "failed",
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": MCP_RESPONSE_SCHEMA_VERSION,
        "status": status,
        "tool_name": tool_name,
        "effect": "none",
        "user_visible_summary": safe_message,
        "mirror_event": None,
        "error": {
            "code": code,
            "category": category,
            "safe_message": safe_message,
        },
    }
    if workflow_run_id:
        payload["workflow_run_id"] = workflow_run_id
    return payload


def recovery_output_response(
    tool_name: str,
    output: Mapping[str, Any],
    *,
    workflow_run_id: str | None,
    mirror_event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    result_status = str(output.get("result_status") or "")
    if result_status == "applied":
        status, effect, summary, error = "completed", "recovery_action_applied", recovery_applied_summary(tool_name), None
    elif result_status == "support_only":
        status, effect, summary, error = "recovery_required", "recovery_support_only", recovery_support_only_summary(tool_name, output), None
    elif result_status == "rejected":
        status, effect, summary = "rejected", "none", recovery_rejected_summary(output)
        error = {"code": "event_scoped_tool_not_available", "category": "contract_validation", "safe_message": summary}
    else:
        status, effect, summary = "failed", "none", "The Kernel could not complete the selected recovery action."
        error = {"code": "kernel_tool_rejected", "category": "contract_validation", "safe_message": summary}
    payload: dict[str, Any] = {
        "schema_version": MCP_RESPONSE_SCHEMA_VERSION,
        "status": status,
        "tool_name": tool_name,
        "effect": effect,
        "user_visible_summary": summary,
        "mirror_event": copy_value(mirror_event) if mirror_event is not None else None,
        "error": error,
    }
    if workflow_run_id:
        payload["workflow_run_id"] = workflow_run_id
    payload.update(extra_fields(output, exclude={"schema_version", "result_status"}))
    validate_mcp_response_envelope(payload)
    return payload


def legacy_retired_response(tool_name: str) -> dict[str, Any]:
    payload = failure_response(
        tool_name,
        code="legacy_kernel_surface_retired",
        category="contract_validation",
        safe_message="The selected legacy Kernel surface is retired. Use the Semantic Control Kernel workflow surface instead.",
        status="rejected",
    )
    payload["error"]["replacement_surface"] = "semantic_control_kernel"  # type: ignore[index]
    payload["error"]["safe_next_actions"] = list(PERMANENT_AGENT_TOOL_NAMES)  # type: ignore[index]
    return payload


def copy_value(value: object) -> Any:
    return deepcopy(value)


def extra_fields(payload: Mapping[str, Any], *, exclude: set[str]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key, value in payload.items():
        if key in exclude or value is None:
            continue
        extras[key] = copy_value(value)
    return extras
