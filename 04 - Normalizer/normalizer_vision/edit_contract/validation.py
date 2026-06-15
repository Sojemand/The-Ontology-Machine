"""Validation helpers for Normalizer edit-contract requests and payloads."""
from __future__ import annotations

from typing import Any

from ..prompts import PROMPT_FIELDS
from . import settings_surface
from . import taxonomy_release_draft
from .types import (
    DESCRIBE_SURFACES_ACTION,
    READ_BUNDLE_ACTION,
    READ_SURFACE_ACTION,
    SOURCE_ACTIONS,
    SURFACE_IDS,
    VALIDATE_SURFACE_ACTION,
    WRITE_SURFACE_ACTION,
)


def require_action(payload: dict) -> str:
    body = request_body(payload)
    action = str(body.get("action", body.get("owner_action", ""))).strip()
    if not action:
        raise ValueError("Aktion fehlt.")
    if action not in {
        DESCRIBE_SURFACES_ACTION,
        READ_BUNDLE_ACTION,
        READ_SURFACE_ACTION,
        VALIDATE_SURFACE_ACTION,
        WRITE_SURFACE_ACTION,
        *SOURCE_ACTIONS,
    }:
        raise ValueError(f"Unbekannte Aktion: {action}")
    return action


def request_body(payload: dict) -> dict[str, Any]:
    if payload.get("schema_version") == "adapter.call_request.v1":
        inner = payload.get("request_payload")
        if isinstance(inner, dict):
            return inner
    return payload


def require_surface_id(payload: dict) -> str:
    surface_id = str(payload.get("surface_id", "")).strip()
    if surface_id not in SURFACE_IDS:
        raise ValueError(f"Unbekannte Surface: {surface_id}")
    return surface_id


def require_surface_value(payload: dict) -> dict[str, Any]:
    value = payload.get("value")
    if not isinstance(value, dict):
        raise ValueError("value muss ein JSON-Objekt sein.")
    return value


def validate_settings_payload(data: dict[str, Any]) -> dict[str, Any]:
    return settings_surface.validate_settings_payload(data)


def validate_prompt_surface_payload(data: dict[str, Any], *, label: str) -> dict[str, str]:
    payload = _require_mapping(data, label=label)
    _require_exact_fields(payload, expected=PROMPT_FIELDS, label=label)
    return {field_name: _required_prompt_string(payload.get(field_name), field_name=field_name) for field_name in PROMPT_FIELDS}


def validate_taxonomy_release_draft_payload(module_root, data: dict[str, Any]) -> dict[str, Any]:
    return taxonomy_release_draft.validate_draft(module_root, _require_mapping(data, label="normalizer.taxonomy_release_draft"))


def flatten_settings(config_dict: dict[str, Any], routing: dict[str, int | float] | None = None) -> dict[str, Any]:
    return settings_surface.flatten_settings(config_dict, routing)


def field_groups() -> list[dict[str, object]]:
    return settings_surface.field_groups()


def routing_settings_from_flat(payload: dict[str, Any]) -> dict[str, int | float]:
    return settings_surface.routing_settings_from_flat(payload)


def _require_mapping(data: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return data


def _require_exact_fields(data: dict[str, Any], *, expected: tuple[str, ...], label: str) -> None:
    unknown = sorted(set(data) - set(expected))
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in expected if field_name not in data]
    if missing:
        raise ValueError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")


def _required_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} muss ein nicht-leerer String sein.")
    return value.strip()


def _required_prompt_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein String sein.")
    return value
