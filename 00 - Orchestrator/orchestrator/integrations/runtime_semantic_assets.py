"""Runtime-semantic asset helpers for run-scoped orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from . import adapter, contract_parsing
from .runtime_semantic_assets_parsing import status_is_ok, unwrap_detail, unwrap_runtime_semantic_assets
from .runtime_semantic_assets_validation import validated_release_detail, validated_runtime_semantic_assets
from .types import ModuleContractError

BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION = "build_runtime_semantic_assets"
READ_ACTIVE_SEMANTIC_RELEASE_ACTION = "read_active_semantic_release"


def read_active_semantic_release(modules: Any, *, corpus_db_path: Path) -> dict[str, Any]:
    direct_reader = getattr(modules, "read_active_semantic_release", None)
    payload = (
        direct_reader(corpus_db_path)
        if callable(direct_reader)
        else _invoke_contract(
            modules,
            "corpus_builder",
            {
                "action": READ_ACTIVE_SEMANTIC_RELEASE_ACTION,
                "corpus_db_path": str(corpus_db_path),
            },
            default_error="Corpus Builder did not provide an active semantic release.",
        )
    )
    return validated_release_detail(unwrap_detail(payload))


def build_runtime_semantic_assets(modules: Any, *, release: dict[str, Any]) -> dict[str, Any]:
    direct_builder = getattr(modules, "build_runtime_semantic_assets", None)
    payload = (
        direct_builder(release)
        if callable(direct_builder)
        else _invoke_contract(
            modules,
            "normalizer",
            {
                "action": BUILD_RUNTIME_SEMANTIC_ASSETS_ACTION,
                "release": release,
            },
            default_error="Normalizer did not provide runtime_semantic_assets.",
        )
    )
    return validated_runtime_semantic_assets(unwrap_runtime_semantic_assets(payload), release=release)


def _invoke_contract(
    modules: Any,
    module_key: str,
    payload: dict[str, Any],
    *,
    default_error: str,
) -> dict[str, Any]:
    runtime_specs = getattr(modules, "_runtime_specs", None)
    if not isinstance(runtime_specs, dict) or module_key not in runtime_specs:
        raise ModuleContractError(f"{module_key} runtime semantics surface is not available.")
    data = adapter.invoke_contract(
        runtime_specs[module_key],
        payload,
        timeout=policy_store.projection_catalog_timeout_seconds(),
    )
    if not status_is_ok(data.get("status")):
        message = contract_parsing.response_error(data) or default_error
        raise ModuleContractError(message)
    return data
