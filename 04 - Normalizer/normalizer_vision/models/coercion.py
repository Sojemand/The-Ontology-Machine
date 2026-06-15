"""Scalar and config coercion helpers for Normalizer Vision."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping

from .types import (
    CONFIG_BOOL_FIELDS,
    CONFIG_INT_FIELDS,
    DEFAULT_MAX_BATCH_FILES,
    DEFAULT_MAX_BATCH_WORKERS,
    DEFAULT_MAX_STRUCTURED_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
)

StringNormalizer = Callable[[str], str]


def coerce_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.strip().replace(",", ".")
        try:
            return float(candidate)
        except ValueError:
            return default
    return default


def coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace(",", ".")))
        except ValueError:
            return default
    return default


def coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "ja", "on"}:
            return True
        if normalized in {"0", "false", "no", "nein", "off", ""}:
            return False
    return default


def coerce_string(value: Any, *, normalize: StringNormalizer | None = None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return normalize(text) if normalize is not None else text
    if isinstance(value, (int, float)):
        text = str(value)
        return normalize(text) if normalize is not None else text
    return None


def string_list(value: Any, *, normalize: StringNormalizer | None = None) -> list[str]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]

    result: list[str] = []
    for item in items:
        text = coerce_string(item, normalize=normalize)
        if text is not None:
            result.append(text)
    return result


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def build_project_config_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    taxonomy_profile_id = data.get("taxonomy_profile_id", "")
    if taxonomy_profile_id is None:
        taxonomy_profile_id = ""
    return {
        "timeout_seconds": int(data.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
        "max_retries": int(data.get("max_retries", 3)),
        "retry_delay_seconds": int(data.get("retry_delay_seconds", 5)),
        "structured_outputs": coerce_bool(data.get("structured_outputs", True), True),
        "default_workers": int(data.get("default_workers", 4)),
        "max_structured_bytes": int(data.get("max_structured_bytes", DEFAULT_MAX_STRUCTURED_BYTES)),
        "max_batch_files": int(data.get("max_batch_files", DEFAULT_MAX_BATCH_FILES)),
        "max_batch_workers": int(data.get("max_batch_workers", DEFAULT_MAX_BATCH_WORKERS)),
        "taxonomy_profile_id": str(taxonomy_profile_id).strip(),
        "projection_hint_mode": str(data.get("projection_hint_mode", "advisory")),
    }
