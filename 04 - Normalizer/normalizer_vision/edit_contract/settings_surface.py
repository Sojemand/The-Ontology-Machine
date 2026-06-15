"""Shared field and validation helpers for `normalizer.settings`."""
from __future__ import annotations

from typing import Any

from ..models import NormalizerProjectConfig
from ..projection_routing.config import default_routing_settings, validate_routing_settings

_TOP_LEVEL_FIELDS = (
    "timeout_seconds",
    "max_retries",
    "retry_delay_seconds",
    "structured_outputs",
    "default_workers",
    "max_structured_bytes",
    "max_batch_files",
    "max_batch_workers",
    "taxonomy_profile_id",
    "projection_hint_mode",
)
_ROUTING_KEYS = tuple(default_routing_settings())
SETTINGS_FIELDS = _TOP_LEVEL_FIELDS + tuple(f"projection_routing.{key}" for key in _ROUTING_KEYS)
SETTINGS_FIELD_GROUPS = (
    ("Execution", ("timeout_seconds", "max_retries", "retry_delay_seconds", "structured_outputs")),
    ("Batch", ("default_workers", "max_structured_bytes", "max_batch_files", "max_batch_workers")),
    ("Taxonomy", ("taxonomy_profile_id", "projection_hint_mode")),
    ("Projection Routing", tuple(f"projection_routing.{key}" for key in _ROUTING_KEYS)),
)
FORBIDDEN_SETTINGS_FIELDS = {
    "provider",
    "model",
    "max_output_tokens",
    "thinking_effort",
    "runtime_settings",
    "api_key",
    "api_base_url",
    "taxonomy_master_path",
    "taxonomy_profile_path",
    "prompt_overrides_path",
    "prompt_bundle_path",
    "semantic_release_recipe_path",
}


def field_groups() -> list[dict[str, object]]:
    return [{"label": label, "fields": list(fields)} for label, fields in SETTINGS_FIELD_GROUPS]


def flatten_settings(
    config_dict: dict[str, Any],
    routing: dict[str, int | float] | None = None,
) -> dict[str, Any]:
    routing_settings = validate_routing_settings(routing if routing is not None else default_routing_settings())
    flattened = {field_name: config_dict[field_name] for field_name in _TOP_LEVEL_FIELDS}
    flattened.update({f"projection_routing.{key}": value for key, value in routing_settings.items()})
    return flattened


def routing_settings_from_flat(payload: dict[str, Any]) -> dict[str, int | float]:
    return {key: payload[f"projection_routing.{key}"] for key in _ROUTING_KEYS}


def validate_settings_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = _require_mapping(data, label="normalizer.settings")
    _require_settings_fields(payload)
    top_level = {
        "timeout_seconds": _required_int(payload.get("timeout_seconds"), field_name="timeout_seconds"),
        "max_retries": _required_int(payload.get("max_retries"), field_name="max_retries"),
        "retry_delay_seconds": _required_int(payload.get("retry_delay_seconds"), field_name="retry_delay_seconds"),
        "structured_outputs": _required_bool(payload.get("structured_outputs"), field_name="structured_outputs"),
        "default_workers": _required_int(payload.get("default_workers"), field_name="default_workers"),
        "max_structured_bytes": _required_int(payload.get("max_structured_bytes"), field_name="max_structured_bytes"),
        "max_batch_files": _required_int(payload.get("max_batch_files"), field_name="max_batch_files"),
        "max_batch_workers": _required_int(payload.get("max_batch_workers"), field_name="max_batch_workers"),
        "taxonomy_profile_id": _optional_string(payload.get("taxonomy_profile_id"), field_name="taxonomy_profile_id"),
        "projection_hint_mode": _required_string(payload.get("projection_hint_mode"), field_name="projection_hint_mode"),
    }
    routing = validate_routing_settings(routing_settings_from_flat(payload))
    NormalizerProjectConfig(**top_level)
    return {**top_level, **{f"projection_routing.{key}": value for key, value in routing.items()}}


def _require_settings_fields(payload: dict[str, Any]) -> None:
    unknown = sorted(set(payload) - set(SETTINGS_FIELDS))
    forbidden = sorted(name for name in unknown if name in FORBIDDEN_SETTINGS_FIELDS)
    if forbidden:
        raise ValueError(
            "normalizer.settings akzeptiert keine orchestrator-, runtime- oder auth-owned Felder: "
            + ", ".join(forbidden)
        )
    if unknown:
        raise ValueError(f"normalizer.settings enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in SETTINGS_FIELDS if field_name not in payload]
    if missing:
        raise ValueError(f"normalizer.settings enthaelt fehlende Felder: {', '.join(missing)}")


def _require_mapping(data: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return data


def _required_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} muss true oder false sein.")
    return value


def _required_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} muss eine Ganzzahl sein.")
    return value


def _required_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} muss ein nicht-leerer String sein.")
    return value.strip()


def _optional_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein String sein.")
    return value.strip()
