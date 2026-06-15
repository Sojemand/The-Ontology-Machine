"""Validation for the orchestrator admin contract."""

from __future__ import annotations

from typing import Any

from ..models import RuntimeSettingsState
from .types import CREDENTIAL_OPERATIONS, CREDENTIAL_TARGETS, RUNTIME_OPERATIONS, SUPPORTED_ACTIONS


def require_action(payload: dict[str, Any]) -> str:
    action = _required_text(payload, "action")
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unknown admin action: {action}")
    return action


def runtime_settings_command(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(payload, {"action", "operation", "settings"})
    operation = _optional_text(payload, "operation") or "read"
    if operation not in RUNTIME_OPERATIONS:
        raise ValueError(f"operation must be one of {', '.join(RUNTIME_OPERATIONS)}.")
    if operation != "write":
        return {"operation": operation}
    settings = _required_mapping(payload, "settings")
    state = RuntimeSettingsState.from_dict(settings)
    state.validate()
    return {"operation": operation, "settings": state.to_dict()}


def credentials_command(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(payload, {"action", "operation", "target", "secret_value"})
    operation = _optional_text(payload, "operation") or "inspect"
    if operation not in CREDENTIAL_OPERATIONS:
        raise ValueError(f"operation must be one of {', '.join(CREDENTIAL_OPERATIONS)}.")
    if operation == "inspect":
        return {"operation": operation}
    target = credential_target(payload)
    if operation == "set_api_key":
        return {"operation": operation, "target": target, "secret_value": _required_text(payload, "secret_value")}
    return {"operation": operation, "target": target}


def reveal_secret_command(payload: dict[str, Any]) -> dict[str, str]:
    _reject_unknown(payload, {"action", "target", "purpose", "unlock_phrase"})
    target = credential_target(payload)
    phrase = _required_text(payload, "unlock_phrase")
    expected = f"REVEAL_SECRET:{target}"
    if phrase != expected:
        raise ValueError("unlock_phrase is invalid.")
    return {"target": target, "purpose": _required_text(payload, "purpose")}


def credential_target(payload: dict[str, Any]) -> str:
    target = _required_text(payload, "target")
    if target not in CREDENTIAL_TARGETS:
        raise ValueError(f"target must be one of {', '.join(CREDENTIAL_TARGETS)}.")
    return target


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a JSON object.")
    return value


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = _optional_text(payload, key)
    if not value:
        raise ValueError(f"{key} is missing or invalid.")
    return value


def _optional_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value.strip()


def _reject_unknown(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")


__all__ = [
    "credential_target",
    "credentials_command",
    "require_action",
    "reveal_secret_command",
    "runtime_settings_command",
]
