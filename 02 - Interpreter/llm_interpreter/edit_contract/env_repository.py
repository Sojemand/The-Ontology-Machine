"""Env-backed surface helpers for the Interpreter edit contract."""
from __future__ import annotations
from typing import Any
from ..models.config import read_env_file
from ..models.types import InterpreterConfig
from ..runtime_paths import ensure_config_dir
from .files import atomic_text_write

RUNTIME_POLICY_FIELDS = ("LOG_LEVEL", "DEBUG_BUNDLE_DIR", "PAGE_ASSET_ALLOWED_ROOTS", "OPENAI_API_BASE_URL")
EXECUTION_LIMIT_FIELDS = (
    "MAX_WORKERS",
    "MAX_PAGE_ASSETS",
    "MAX_PAGE_ASSET_BYTES",
    "MAX_REQUEST_ASSET_BYTES",
    "TIMEOUT_SECONDS",
    "MAX_RETRIES",
    "RETRY_DELAY_SECONDS",
)
ENV_FIELD_ORDER = RUNTIME_POLICY_FIELDS + EXECUTION_LIMIT_FIELDS
RUNTIME_POLICY_FIELD_GROUPS = (
    ("Runtime Policy", ("LOG_LEVEL", "DEBUG_BUNDLE_DIR", "PAGE_ASSET_ALLOWED_ROOTS")),
    ("Advanced", ("OPENAI_API_BASE_URL",)),
)
EXECUTION_LIMIT_FIELD_GROUPS = (
    ("Assets/Runtime", ("MAX_WORKERS", "MAX_PAGE_ASSETS", "MAX_PAGE_ASSET_BYTES", "MAX_REQUEST_ASSET_BYTES", "TIMEOUT_SECONDS")),
    ("Retries", ("MAX_RETRIES", "RETRY_DELAY_SECONDS")),
)

_NON_NEGATIVE_FIELDS = {"MAX_RETRIES", "RETRY_DELAY_SECONDS"}
_POSITIVE_FIELDS = set(EXECUTION_LIMIT_FIELDS) - _NON_NEGATIVE_FIELDS
_LOG_LEVEL_DEFAULT = "INFO"


def read_runtime_policy(paths) -> dict[str, str]:
    values = _validated_env_snapshot(paths)
    return {key: values[key] for key in RUNTIME_POLICY_FIELDS}


def write_runtime_policy(paths, payload: dict[str, Any]) -> dict[str, str]:
    values = _validated_env_snapshot(paths)
    values.update(validate_runtime_policy(payload))
    _write_env_file(paths, values)
    return read_runtime_policy(paths)


def read_execution_limits(paths) -> dict[str, Any]:
    raw = read_env_file(paths.env_file)
    payload = {key: raw.get(key, _default_env_strings()[key]) for key in EXECUTION_LIMIT_FIELDS}
    return validate_execution_limits(payload)


def write_execution_limits(paths, payload: dict[str, Any]) -> dict[str, Any]:
    values = _validated_env_snapshot(paths)
    values.update(_execution_limits_to_env(validate_execution_limits(payload)))
    _write_env_file(paths, values)
    return read_execution_limits(paths)


def validate_runtime_policy(payload: dict[str, Any]) -> dict[str, str]:
    _require_exact_fields(payload, RUNTIME_POLICY_FIELDS, label="runtime_policy_env")
    config = InterpreterConfig()
    return {
        "LOG_LEVEL": _normalize_string(payload["LOG_LEVEL"], default=_LOG_LEVEL_DEFAULT),
        "DEBUG_BUNDLE_DIR": _normalize_string(payload["DEBUG_BUNDLE_DIR"]),
        "PAGE_ASSET_ALLOWED_ROOTS": _normalize_string(payload["PAGE_ASSET_ALLOWED_ROOTS"]),
        "OPENAI_API_BASE_URL": _normalize_string(payload["OPENAI_API_BASE_URL"], default=config.api_base_url),
    }


def validate_execution_limits(payload: dict[str, Any]) -> dict[str, Any]:
    _require_exact_fields(payload, EXECUTION_LIMIT_FIELDS, label="execution_limits")
    normalized = {key: _parse_int(payload[key], key) for key in EXECUTION_LIMIT_FIELDS}
    for key in _POSITIVE_FIELDS:
        if normalized[key] <= 0:
            raise ValueError(f"{key} muss > 0 sein.")
    for key in _NON_NEGATIVE_FIELDS:
        if normalized[key] < 0:
            raise ValueError(f"{key} muss >= 0 sein.")
    return normalized


def field_groups(groups: tuple[tuple[str, tuple[str, ...]], ...]) -> list[dict[str, object]]:
    return [{"label": label, "fields": list(fields)} for label, fields in groups]


def _validated_env_snapshot(paths) -> dict[str, str]:
    raw = read_env_file(paths.env_file)
    values = _default_env_strings()
    values.update(validate_runtime_policy({key: raw.get(key, values[key]) for key in RUNTIME_POLICY_FIELDS}))
    execution = validate_execution_limits({key: raw.get(key, values[key]) for key in EXECUTION_LIMIT_FIELDS})
    values.update(_execution_limits_to_env(execution))
    return values


def _default_env_strings() -> dict[str, str]:
    config = InterpreterConfig()
    return {
        "LOG_LEVEL": _LOG_LEVEL_DEFAULT,
        "DEBUG_BUNDLE_DIR": "",
        "PAGE_ASSET_ALLOWED_ROOTS": "",
        "OPENAI_API_BASE_URL": config.api_base_url,
        "MAX_WORKERS": str(config.max_workers),
        "MAX_PAGE_ASSETS": str(config.max_page_assets),
        "MAX_PAGE_ASSET_BYTES": str(config.max_page_asset_bytes),
        "MAX_REQUEST_ASSET_BYTES": str(config.max_request_asset_bytes),
        "TIMEOUT_SECONDS": str(config.timeout_seconds),
        "MAX_RETRIES": str(config.max_retries),
        "RETRY_DELAY_SECONDS": str(config.retry_delay_seconds),
    }


def _execution_limits_to_env(payload: dict[str, Any]) -> dict[str, str]:
    return {key: str(int(payload[key])) for key in EXECUTION_LIMIT_FIELDS}


def _write_env_file(paths, values: dict[str, str]) -> None:
    ensure_config_dir(paths)
    text = "\n".join(f"{key}={values[key]}" for key in ENV_FIELD_ORDER) + "\n"
    atomic_text_write(paths.env_file, text)


def _parse_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} muss eine Ganzzahl sein.")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} muss eine Ganzzahl sein.") from None


def _normalize_string(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _require_exact_fields(payload: dict[str, Any], expected: tuple[str, ...], *, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    missing = [key for key in expected if key not in payload]
    extras = [key for key in payload if key not in expected]
    if missing or extras:
        details = []
        if missing:
            details.append(f"fehlend: {', '.join(missing)}")
        if extras:
            details.append(f"unerlaubt: {', '.join(extras)}")
        raise ValueError(f"{label} hat ungueltige Felder ({'; '.join(details)}).")


__all__ = ["ENV_FIELD_ORDER", "EXECUTION_LIMIT_FIELD_GROUPS", "EXECUTION_LIMIT_FIELDS", "RUNTIME_POLICY_FIELDS", "RUNTIME_POLICY_FIELD_GROUPS", "field_groups", "read_execution_limits", "read_runtime_policy", "validate_execution_limits", "validate_runtime_policy", "write_execution_limits", "write_runtime_policy"]
