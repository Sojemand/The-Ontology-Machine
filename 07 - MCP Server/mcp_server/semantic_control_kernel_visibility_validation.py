from __future__ import annotations

import hmac
import os
from typing import Any


HOST_BRIDGE_TOKEN_ENV = "VISION_MCP_HOST_BRIDGE_TOKEN"
HOST_BRIDGE_TOKEN_FIELD = "host_bridge_token"


def error_response(
    tool_name: str,
    *,
    code: str,
    safe_message: str,
    status: str = "failed",
) -> dict[str, Any]:
    return {
        "schema_version": "semantic_control_kernel.mcp_response.v1",
        "status": status,
        "tool_name": tool_name,
        "effect": "none",
        "user_visible_summary": safe_message,
        "mirror_event": None,
        "error": {
            "code": code,
            "category": "contract_validation",
            "safe_message": safe_message,
        },
    }


def missing_required_scope_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field_name in fields:
        value = payload.get(field_name)
        if field_name == "arguments":
            if not isinstance(value, dict):
                return True
            continue
        if field_name == "input_refs":
            if not isinstance(value, list):
                return True
            continue
        if not isinstance(value, str) or not value.strip():
            return True
    return False


def unexpected_scope_fields(payload: dict[str, Any], allowed: set[str]) -> list[str]:
    return sorted(field_name for field_name in payload if field_name not in allowed)


def host_only_bridge_payload_allowed(payload: dict[str, Any], required: tuple[str, ...]) -> bool:
    for field_name in required:
        value = payload.get(field_name)
        if field_name in {"response", "target_identity", "state_snapshot_identity"}:
            if not isinstance(value, dict):
                return False
            continue
        if field_name == "response_status":
            if not isinstance(value, str) or not value.strip():
                return False
            continue
        if not isinstance(value, str) or not value.strip():
            return False
    return bool(str(payload.get("host_surface_identity") or "") and str(payload.get("client_request_id") or ""))


def host_only_bridge_token_allowed(payload: dict[str, Any]) -> bool:
    expected = str(os.environ.get(HOST_BRIDGE_TOKEN_ENV) or "").strip()
    provided = payload.get(HOST_BRIDGE_TOKEN_FIELD)
    if not expected or not isinstance(provided, str) or not provided.strip():
        return False
    return hmac.compare_digest(provided, expected)


def clean(value: str) -> str:
    return str(value or "").strip()
