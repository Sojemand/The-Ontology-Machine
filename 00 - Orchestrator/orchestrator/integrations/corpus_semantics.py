"""Corpus-semantic status helpers for Orchestrator UX flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from . import adapter, contract_parsing
from .runtime_semantic_assets_parsing import status_is_ok, unwrap_detail
from .types import ModuleContractError

SEMANTIC_STATUS_ACTION = "semantic_status"


def semantic_status(modules: Any, *, corpus_db_path: Path | None = None) -> dict[str, Any]:
    direct_reader = getattr(modules, "semantic_status", None)
    payload = (
        direct_reader(corpus_db_path)
        if callable(direct_reader)
        else _invoke_contract(
            modules,
            {
                "action": SEMANTIC_STATUS_ACTION,
                **({"corpus_db_path": str(corpus_db_path)} if corpus_db_path is not None else {}),
            },
        )
    )
    detail = unwrap_detail(payload)
    if not isinstance(detail, dict):
        raise ModuleContractError("semantic_status did not provide a JSON object.")
    if not status_is_ok(detail.get("status")):
        message = contract_parsing.response_error(detail) or "Semantic status could not be loaded."
        raise ModuleContractError(message)
    return detail


def _invoke_contract(modules: Any, payload: dict[str, Any]) -> dict[str, Any]:
    runtime_specs = getattr(modules, "_runtime_specs", None)
    if not isinstance(runtime_specs, dict) or "corpus_builder" not in runtime_specs:
        raise ModuleContractError("Corpus Builder semantic status surface is not available.")
    data = adapter.invoke_contract(
        runtime_specs["corpus_builder"],
        payload,
        timeout=policy_store.projection_catalog_timeout_seconds(),
    )
    if not status_is_ok(data.get("status")):
        message = contract_parsing.response_error(data) or "Semantic status could not be loaded."
        raise ModuleContractError(message)
    return data


__all__ = ["semantic_status"]
