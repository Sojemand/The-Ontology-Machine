"""Default taxonomy package helpers for database creation UX."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import policy_store
from . import adapter, contract_parsing
from .runtime_semantic_assets_parsing import require_dict, require_list, require_text, status_is_ok
from .types import ModuleContractError

LIST_DEFAULT_BLUEPRINTS_ACTION = "list_default_blueprints"
EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION = "export_default_blueprint_release"


def list_default_blueprints(modules: Any) -> list[dict[str, Any]]:
    direct_reader = getattr(modules, "list_default_blueprints", None)
    payload = (
        direct_reader()
        if callable(direct_reader)
        else _invoke_contract(
            modules,
            {
                "action": LIST_DEFAULT_BLUEPRINTS_ACTION,
            },
            default_error="Normalizer did not provide default blueprints.",
        )
    )
    if not isinstance(payload, dict):
        raise ModuleContractError("list_default_blueprints did not provide a JSON object.")
    if not status_is_ok(payload.get("status")):
        message = contract_parsing.response_error(payload) or "Normalizer did not provide default blueprints."
        raise ModuleContractError(message)
    blueprints = require_list(payload.get("blueprints"), "blueprints")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(blueprints):
        blueprint = require_dict(item, f"blueprints[{index}]")
        require_text(blueprint.get("blueprint_ref"), f"blueprints[{index}].blueprint_ref")
        result.append(blueprint)
    return result


def export_default_blueprint_release(
    modules: Any,
    *,
    blueprint_ref: str,
    target_locale: str | None = None,
    output_path: Path,
) -> dict[str, Any]:
    direct_exporter = getattr(modules, "export_default_blueprint_release", None)
    payload = (
        direct_exporter(blueprint_ref, output_path, target_locale=target_locale)
        if callable(direct_exporter)
        else _invoke_contract(
            modules,
            {
                "action": EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION,
                "blueprint_ref": str(blueprint_ref),
                "target_locale": str(target_locale or "").strip(),
                "output_path": str(output_path),
            },
            default_error="Normalizer could not export a blueprint release.",
        )
    )
    if not isinstance(payload, dict):
        raise ModuleContractError("export_default_blueprint_release did not provide a JSON object.")
    if not status_is_ok(payload.get("status")):
        message = contract_parsing.response_error(payload) or "Normalizer could not export a blueprint release."
        raise ModuleContractError(message)
    detail = require_dict(payload, "blueprint_release")
    require_text(detail.get("blueprint_ref"), "blueprint_ref")
    require_text(detail.get("output_path"), "output_path")
    require_text(detail.get("release_id"), "release_id")
    require_text(detail.get("release_version"), "release_version")
    return detail


def _invoke_contract(
    modules: Any,
    payload: dict[str, Any],
    *,
    default_error: str,
) -> dict[str, Any]:
    runtime_specs = getattr(modules, "_runtime_specs", None)
    if not isinstance(runtime_specs, dict) or "normalizer" not in runtime_specs:
        raise ModuleContractError("Normalizer blueprint surface is not available.")
    data = adapter.invoke_contract(
        runtime_specs["normalizer"],
        payload,
        timeout=policy_store.projection_catalog_timeout_seconds(),
    )
    if not status_is_ok(data.get("status")):
        message = contract_parsing.response_error(data) or default_error
        raise ModuleContractError(message)
    return data


__all__ = [
    "EXPORT_DEFAULT_BLUEPRINT_RELEASE_ACTION",
    "LIST_DEFAULT_BLUEPRINTS_ACTION",
    "export_default_blueprint_release",
    "list_default_blueprints",
]
