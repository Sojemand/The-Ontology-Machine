"""Parsing helpers for runtime-semantic contract payloads."""

from __future__ import annotations

from typing import Any

from . import contract_parsing
from .types import ModuleContractError


def status_is_ok(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().upper() == "OK"


def unwrap_detail(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModuleContractError("read_active_semantic_release did not provide a JSON object.")
    detail = payload.get("detail")
    if detail is None:
        return payload
    if not isinstance(detail, dict):
        raise ModuleContractError("read_active_semantic_release.detail is invalid.")
    if not status_is_ok(payload.get("status")):
        message = contract_parsing.response_error(payload) or "Active semantic release could not be read."
        raise ModuleContractError(message)
    return detail


def unwrap_runtime_semantic_assets(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModuleContractError("build_runtime_semantic_assets did not provide a JSON object.")
    assets = payload.get("runtime_semantic_assets")
    if assets is None:
        return payload
    if not isinstance(assets, dict):
        raise ModuleContractError("runtime_semantic_assets is invalid.")
    if not status_is_ok(payload.get("status")):
        message = contract_parsing.response_error(payload) or "runtime_semantic_assets could not be built."
        raise ModuleContractError(message)
    return assets


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModuleContractError(f"{label} must be a JSON object.")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ModuleContractError(f"{label} must be a list.")
    return value


def require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ModuleContractError(f"{label} is missing.")
    return text


def require_optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def require_canonical_runtime_locale(value: str | None, label: str) -> str | None:
    if value is not None and value != "en":
        raise ModuleContractError(f"{label} must be en.")
    return value


def require_matching_text(value: Any, label: str, expected: str, mismatch_message: str) -> str:
    text = require_text(value, label)
    if text != expected:
        raise ModuleContractError(mismatch_message)
    return text


def require_matching_optional_text(
    value: Any,
    label: str,
    expected: str | None,
    mismatch_message: str,
) -> str | None:
    text = require_optional_text(value, label)
    if text != expected and (text is not None or expected is not None):
        raise ModuleContractError(mismatch_message)
    return text
