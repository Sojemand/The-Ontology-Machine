from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

ALLOWED_ACTIONS: tuple[str, ...] = ()


def _response_path_from_args(argv: list[str]) -> Path | None:
    for index, token in enumerate(argv):
        if token == "--response" and index + 1 < len(argv):
            return Path(argv[index + 1])
    return None


def _write_response(path: Path, payload: dict[str, object]) -> None:
    from semantic_control_kernel.repository.atomic_json import atomic_write_json

    atomic_write_json(path, payload, sort_keys=False, ensure_ascii=True)


def _error_payload(*, code: str, message: str, request_id: str | None = None, action: str | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if action is not None:
        error["action"] = action
        error["allowed_actions"] = list(ALLOWED_ACTIONS)
    return {"status": "error", "request_id": request_id, "error": error}


def _parse_cli(argv: list[str]) -> tuple[Path, Path]:
    if len(argv) != 4:
        raise ValueError("Expected --request <request.json> --response <response.json>.")
    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token not in {"--request", "--response"} or index + 1 >= len(argv):
            raise ValueError("Expected --request <request.json> --response <response.json>.")
        if token in values:
            raise ValueError(f"Duplicate argument: {token}")
        values[token] = argv[index + 1]
        index += 2
    if "--request" not in values or "--response" not in values:
        raise ValueError("Expected --request <request.json> --response <response.json>.")
    return Path(values["--request"]), Path(values["--response"])


def _load_request(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Request JSON root must be an object.")
    return payload


def _request_id(payload: dict[str, object]) -> str | None:
    value = payload.get("request_id")
    return value if isinstance(value, str) else None


def _action(payload: dict[str, object]) -> str:
    value = payload.get("action")
    if not isinstance(value, str) or not value:
        raise ValueError("Request field 'action' must be a non-empty string.")
    return value


def _validate_payload(payload: dict[str, object]) -> None:
    if "payload" in payload and not isinstance(payload["payload"], dict):
        raise ValueError("Request field 'payload' must be an object when present.")


def _payload(payload: dict[str, object]) -> dict[str, object]:
    value = payload.get("payload", {})
    if not isinstance(value, dict):
        raise ValueError("Request field 'payload' must be an object when present.")
    return value


def _is_agent_surface_action(action: str) -> bool:
    from semantic_control_kernel.services.agent_tool_invocation_service import (
        is_event_scoped_recovery_tool_name,
        is_permanent_agent_tool_name,
        is_rejected_legacy_agent_surface_name,
    )

    return (
        is_permanent_agent_tool_name(action)
        or is_rejected_legacy_agent_surface_name(action)
        or is_event_scoped_recovery_tool_name(action)
    )


def _split_agent_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from semantic_control_kernel.types.agent_tools import ALLOWED_INVOCATION_CONTEXT_FIELDS

    if not payload:
        return {}, {}
    if "invocation_context" in payload or "model_payload" in payload:
        invocation_context = payload.get("invocation_context", {})
        model_payload = payload.get("model_payload", {})
        if not isinstance(invocation_context, dict):
            raise ValueError("payload.invocation_context must be an object when present.")
        if not isinstance(model_payload, dict):
            raise ValueError("payload.model_payload must be an object when present.")
        unexpected = sorted(set(payload) - {"invocation_context", "model_payload"})
        if unexpected:
            model_payload = {**model_payload, **{field: payload[field] for field in unexpected}}
        return dict(invocation_context), dict(model_payload)
    if set(payload).issubset(ALLOWED_INVOCATION_CONTEXT_FIELDS):
        return dict(payload), {}
    return {}, dict(payload)


def _handled_action_payload(action: str, payload: Mapping[str, Any]) -> dict[str, object]:
    from semantic_control_kernel.surface.agent_invocation import invoke_agent_tool

    invocation_context, model_payload = _split_agent_payload(payload)
    result = invoke_agent_tool(action, invocation_context=invocation_context, model_payload=model_payload)
    return {"status": "ok", "result": result.to_dict()}


def _legacy_request_shell(argv: list[str]) -> int:
    response_path = _response_path_from_args(argv)
    request_id: str | None = None
    try:
        request_path, response_path = _parse_cli(argv)
        request = _load_request(request_path)
        request_id = _request_id(request)
        action = _action(request)
        _validate_payload(request)
        if _is_agent_surface_action(action):
            response = _handled_action_payload(action, _payload(request))
            response["request_id"] = request_id
            _write_response(response_path, response)
            return 0
        _write_response(response_path, _error_payload(code="unknown_action", message=f"Unknown Semantic Control Kernel action: {action}", request_id=request_id, action=action))
        return 0
    except Exception as exc:
        if response_path is not None:
            try:
                _write_response(response_path, _error_payload(code="invalid_request", message=str(exc), request_id=request_id))
            except Exception:
                pass
        print(f"Semantic Control Kernel contract request failed: {exc}", file=sys.stderr)
        return 1
