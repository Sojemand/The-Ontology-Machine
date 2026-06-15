"""Semantic-release preflight helpers for orchestrator-facing flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from . import adapter, contract_parsing
from .runtime_semantic_assets_parsing import status_is_ok
from .types import ModuleContractError

ACTIVATION_PREFLIGHT_ACTION = "activation_preflight"


def activation_preflight(modules: Any, *, release_path: Path, corpus_db_path: Path) -> dict[str, Any]:
    direct_preflight = getattr(modules, "activation_preflight", None)
    payload = (
        direct_preflight(release_path, corpus_db_path)
        if callable(direct_preflight)
        else _invoke_contract(
            modules,
            {
                "action": ACTIVATION_PREFLIGHT_ACTION,
                "release_path": str(release_path),
                "corpus_db_path": str(corpus_db_path),
            },
        )
    )
    return _unwrap_activation_preflight_detail(payload)


def _invoke_contract(modules: Any, payload: dict[str, Any]) -> dict[str, Any]:
    runtime_specs = getattr(modules, "_runtime_specs", None)
    if not isinstance(runtime_specs, dict) or "corpus_builder" not in runtime_specs:
        raise ModuleContractError("Corpus Builder release preflight is not available.")
    return adapter.invoke_contract(
        runtime_specs["corpus_builder"],
        payload,
        timeout=policy_store.projection_catalog_timeout_seconds(),
    )


def _unwrap_activation_preflight_detail(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModuleContractError("activation_preflight did not provide a JSON object.")
    detail = payload.get("detail")
    if detail is None:
        detail = payload
    if not isinstance(detail, dict):
        raise ModuleContractError("activation_preflight.detail is invalid.")
    if not status_is_ok(payload.get("status")):
        message = contract_parsing.response_error(payload) or "Semantic activation preflight failed."
        raise ModuleContractError(message)
    return detail


__all__ = ["ACTIVATION_PREFLIGHT_ACTION", "activation_preflight"]
