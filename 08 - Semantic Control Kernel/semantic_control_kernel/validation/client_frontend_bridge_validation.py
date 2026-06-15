from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from semantic_control_kernel.types.client_frontend_bridge import (
    CLIENT_EVENTS_REQUEST_SCHEMA_VERSION,
    EVENT_SCOPED_TOOL_DEFINITIONS_REQUEST_SCHEMA_VERSION,
    EVENT_SCOPED_TOOL_DEFINITIONS_RESPONSE_SCHEMA_VERSION,
    HOST_BRIDGE_RESPONSE_SCHEMA_VERSION,
    HOST_BRIDGE_RESPONSE_STATUSES,
    INTERACTION_CANCEL_REQUEST_SCHEMA_VERSION,
    INTERACTION_RESPONSE_SUBMIT_SCHEMA_VERSION,
)
from semantic_control_kernel.types.events import ClientFrontendEventBatch, UserInteractionResponse
from semantic_control_kernel.validation.contract_validation import validate_contract


class ClientFrontendBridgeValidationError(ValueError):
    pass


def validate_client_events_request(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, CLIENT_EVENTS_REQUEST_SCHEMA_VERSION)
    _optional_string(payload, "cursor")
    _optional_limit(payload)
    _require_string(payload, "host_surface_identity")
    _require_string(payload, "client_instance_id")
    _require_string(payload, "client_request_id")


def validate_interaction_response_submit_request(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, INTERACTION_RESPONSE_SUBMIT_SCHEMA_VERSION)
    _require_string(payload, "interaction_request_id")
    response = payload.get("response")
    if not isinstance(response, Mapping):
        raise ClientFrontendBridgeValidationError("response must be an object.")
    validate_contract(dict(response), expected_schema_version=UserInteractionResponse.SCHEMA_VERSION)
    for field_name in ("target_identity", "state_snapshot_identity"):
        if not isinstance(payload.get(field_name), Mapping):
            raise ClientFrontendBridgeValidationError(f"{field_name} must be an object.")
    _require_string(payload, "host_surface_identity")
    _require_string(payload, "client_request_id")


def validate_interaction_cancel_request(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, INTERACTION_CANCEL_REQUEST_SCHEMA_VERSION)
    _require_string(payload, "interaction_request_id")
    _require_string(payload, "response_status")
    if payload["response_status"] not in {"cancelled", "closed", "expired"}:
        raise ClientFrontendBridgeValidationError("response_status must be cancelled, closed or expired.")
    for field_name in ("target_identity", "state_snapshot_identity"):
        if not isinstance(payload.get(field_name), Mapping):
            raise ClientFrontendBridgeValidationError(f"{field_name} must be an object.")
    _require_string(payload, "host_surface_identity")
    _require_string(payload, "client_request_id")


def validate_event_scoped_tool_definitions_request(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, EVENT_SCOPED_TOOL_DEFINITIONS_REQUEST_SCHEMA_VERSION)
    for field_name in ("mirror_event_id", "recovery_event_id", "state_snapshot_id", "host_surface_identity", "client_request_id"):
        _require_string(payload, field_name)


def validate_host_bridge_response(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, HOST_BRIDGE_RESPONSE_SCHEMA_VERSION)
    _require_string(payload, "status")
    if payload["status"] not in HOST_BRIDGE_RESPONSE_STATUSES:
        raise ClientFrontendBridgeValidationError(f"Unknown host bridge status: {payload['status']!r}")
    _require_string(payload, "user_visible_summary")
    _optional_string(payload, "interaction_request_id")
    error = payload.get("error")
    if error is not None and not isinstance(error, Mapping):
        raise ClientFrontendBridgeValidationError("error must be null or an object.")


def validate_event_scoped_tool_definitions_response(payload: Mapping[str, Any]) -> None:
    _require_schema(payload, EVENT_SCOPED_TOOL_DEFINITIONS_RESPONSE_SCHEMA_VERSION)
    for field_name in ("mirror_event_id", "recovery_event_id", "state_snapshot_id", "status"):
        _require_string(payload, field_name)
    tools = payload.get("tool_definitions")
    if not isinstance(tools, list):
        raise ClientFrontendBridgeValidationError("tool_definitions must be a list.")


def validate_client_frontend_event_batch(payload: Mapping[str, Any]) -> None:
    validate_contract(dict(payload), expected_schema_version=ClientFrontendEventBatch.SCHEMA_VERSION)


def _require_schema(payload: Mapping[str, Any] | object, schema_version: str) -> None:
    if not isinstance(payload, Mapping):
        raise ClientFrontendBridgeValidationError(f"{schema_version} must be an object.")
    if payload.get("schema_version") != schema_version:
        raise ClientFrontendBridgeValidationError(f"Expected schema_version {schema_version!r}.")


def _require_string(payload: Mapping[str, Any], field_name: str) -> None:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ClientFrontendBridgeValidationError(f"{field_name} must be a non-empty string.")


def _optional_string(payload: Mapping[str, Any], field_name: str) -> None:
    if field_name not in payload or payload[field_name] in (None, ""):
        return
    if not isinstance(payload[field_name], str):
        raise ClientFrontendBridgeValidationError(f"{field_name} must be a string when present.")


def _optional_limit(payload: Mapping[str, Any]) -> None:
    if "limit" not in payload or payload["limit"] in (None, ""):
        return
    value = payload["limit"]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ClientFrontendBridgeValidationError("limit must be a positive integer when present.")
