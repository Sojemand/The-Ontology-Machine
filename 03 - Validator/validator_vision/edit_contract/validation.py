"""Validation helpers for validator edit-contract requests and payloads."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import config as config_models
from .types import DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, SURFACE_IDS, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION

CHECK_FIELDS = ("free_text", "context_scalars", "content_fields", "rows")
MATCH_FIELDS = ("scalar_level", "row_level", "require_free_text", "number_tolerance_absolute", "min_string_length", "min_compact_length", "context_fields", "skip_content_fields", "skip_row_fields", "row_anchor_keys")
SETTINGS_FIELDS = tuple([f"checks.{name}" for name in CHECK_FIELDS] + [f"match.{name}" for name in MATCH_FIELDS])
POLICY_FIELDS = ("flag_needs_review", "max_issues_per_check")
_BOOL_FIELDS = {"checks.free_text", "checks.context_scalars", "checks.content_fields", "checks.rows", "match.require_free_text", "flag_needs_review"}
_INT_FIELDS = {"match.min_string_length", "match.min_compact_length", "max_issues_per_check"}
_FLOAT_FIELDS = {"match.number_tolerance_absolute"}
_LIST_FIELDS = {"match.context_fields", "match.skip_content_fields", "match.skip_row_fields", "match.row_anchor_keys"}
_FULL_FIELDS = {"checks", "match", "flag_needs_review", "max_issues_per_check"}

def require_action(payload: dict) -> str:
    action = str(payload.get("action", "")).strip()
    if not action:
        raise ValueError("Aktion fehlt.")
    if action not in {DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION}:
        raise ValueError(f"Unbekannte Aktion: {action}")
    return action

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

def read_full_payload(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return _normalize_full_payload({})
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config ist kein gueltiges JSON: {config_path} ({exc})") from exc
    return _normalize_full_payload(raw)

def validate_settings_payload(data: dict[str, Any]) -> dict[str, Any]:
    return settings_slice(_merge_settings(default_full_payload(), _normalize_slice(data, expected=SETTINGS_FIELDS, label="validator.settings")))

def validate_report_policy_payload(data: dict[str, Any]) -> dict[str, Any]:
    return policy_slice(_merge_policy(default_full_payload(), _normalize_slice(data, expected=POLICY_FIELDS, label="validator.report_preview_policy")))

def merge_settings_payload(full_payload: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return _merge_settings(full_payload, _normalize_slice(data, expected=SETTINGS_FIELDS, label="validator.settings"))

def merge_policy_payload(full_payload: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return _merge_policy(full_payload, _normalize_slice(data, expected=POLICY_FIELDS, label="validator.report_preview_policy"))

def settings_slice(full_payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_full_payload(full_payload)
    return {key: payload[key.split(".", 1)[0]][key.split(".", 1)[1]] for key in SETTINGS_FIELDS}

def policy_slice(full_payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_full_payload(full_payload)
    return {key: payload[key] for key in POLICY_FIELDS}

def default_full_payload() -> dict[str, Any]:
    return asdict(config_models.ValidatorConfig())

def _merge_settings(full_payload: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    merged = _normalize_full_payload(full_payload)
    merged["checks"] = {name: values[f"checks.{name}"] for name in CHECK_FIELDS}
    merged["match"] = {name: values[f"match.{name}"] for name in MATCH_FIELDS}
    return _normalize_full_payload(merged)

def _merge_policy(full_payload: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    merged = _normalize_full_payload(full_payload)
    for key in POLICY_FIELDS:
        merged[key] = values[key]
    return _normalize_full_payload(merged)

def _normalize_slice(data: dict[str, Any], *, expected: tuple[str, ...], label: str) -> dict[str, Any]:
    payload = _require_mapping(data, label=label)
    _require_exact_fields(payload, expected=expected, label=label)
    return {field_name: _normalize_leaf(field_name, payload[field_name]) for field_name in expected}

def _normalize_full_payload(data: Any) -> dict[str, Any]:
    payload = _require_mapping(data, label="config.json") if data is not None else {}
    unknown = sorted(set(payload) - _FULL_FIELDS)
    if unknown:
        raise ValueError(f"config.json enthaelt unbekannte Felder: {', '.join(unknown)}")
    defaults = config_models.ValidatorConfig()
    checks = _require_mapping(payload.get("checks"), label="checks") if "checks" in payload else {}
    match = _require_mapping(payload.get("match"), label="match") if "match" in payload else {}
    _require_exact_fields(checks, expected=CHECK_FIELDS, label="checks", allow_missing=True)
    _require_exact_fields(match, expected=MATCH_FIELDS, label="match", allow_missing=True)
    cfg = config_models.ValidatorConfig(
        checks=config_models.CheckToggles(**{name: _normalize_bool(checks.get(name, getattr(defaults.checks, name)), field_name=f"checks.{name}") for name in CHECK_FIELDS}),
        match=config_models.MatchConfig(
            scalar_level=_normalize_string(match.get("scalar_level", defaults.match.scalar_level), field_name="match.scalar_level"),
            row_level=_normalize_string(match.get("row_level", defaults.match.row_level), field_name="match.row_level"),
            require_free_text=_normalize_bool(match.get("require_free_text", defaults.match.require_free_text), field_name="match.require_free_text"),
            number_tolerance_absolute=_normalize_float(match.get("number_tolerance_absolute", defaults.match.number_tolerance_absolute), field_name="match.number_tolerance_absolute"),
            min_string_length=_normalize_int(match.get("min_string_length", defaults.match.min_string_length), field_name="match.min_string_length"),
            min_compact_length=_normalize_int(match.get("min_compact_length", defaults.match.min_compact_length), field_name="match.min_compact_length"),
            context_fields=_normalize_string_list(match.get("context_fields", defaults.match.context_fields), field_name="match.context_fields"),
            skip_content_fields=_normalize_string_list(match.get("skip_content_fields", defaults.match.skip_content_fields), field_name="match.skip_content_fields"),
            skip_row_fields=_normalize_string_list(match.get("skip_row_fields", defaults.match.skip_row_fields), field_name="match.skip_row_fields"),
            row_anchor_keys=_normalize_string_list(match.get("row_anchor_keys", defaults.match.row_anchor_keys), field_name="match.row_anchor_keys"),
        ),
        flag_needs_review=_normalize_bool(payload.get("flag_needs_review", defaults.flag_needs_review), field_name="flag_needs_review"),
        max_issues_per_check=_normalize_int(payload.get("max_issues_per_check", defaults.max_issues_per_check), field_name="max_issues_per_check"),
    )
    config_models._validate_config(cfg)
    return asdict(cfg)

def _normalize_leaf(field_name: str, value: Any) -> Any:
    if field_name in _BOOL_FIELDS:
        return _normalize_bool(value, field_name=field_name)
    if field_name in _INT_FIELDS:
        return _normalize_int(value, field_name=field_name)
    if field_name in _FLOAT_FIELDS:
        return _normalize_float(value, field_name=field_name)
    if field_name in _LIST_FIELDS:
        return _normalize_string_list(value, field_name=field_name)
    return _normalize_string(value, field_name=field_name)

def _require_mapping(data: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return data

def _require_exact_fields(data: dict[str, Any], *, expected: tuple[str, ...], label: str, allow_missing: bool = False) -> None:
    unknown = sorted(set(data) - set(expected))
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    if allow_missing:
        return
    missing = [name for name in expected if name not in data]
    if missing:
        raise ValueError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")

def _normalize_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} muss true oder false sein")
    return value

def _normalize_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} muss eine Ganzzahl sein")
    return value

def _normalize_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} muss eine Zahl sein")
    return float(value)

def _normalize_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein String sein")
    return value

def _normalize_string_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} muss eine Liste von Strings sein")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{field_name}[{index}] muss ein String sein")
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return items
