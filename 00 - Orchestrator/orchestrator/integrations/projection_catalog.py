"""Projection-catalog boundary helpers for explicit Admin-/Debug-Routing."""

from __future__ import annotations

from typing import Any

from .. import policy_store
from . import adapter, contract_parsing
from .types import ModuleContractError

BUILD_PROJECTION_CATALOG_ACTION = "build_projection_catalog"
_OPTIONAL_CATALOG_METADATA_FIELDS = (
    "release_id",
    "release_version",
    "release_fingerprint",
    "master_taxonomy_id",
    "master_taxonomy_release_id",
    "runtime_locale",
)


def load_normalizer_projection_catalog(modules: Any) -> dict[str, Any] | None:
    direct_builder = getattr(modules, "build_projection_catalog", None)
    if callable(direct_builder):
        return _validated_catalog(direct_builder())
    runtime_specs = getattr(modules, "_runtime_specs", None)
    if not isinstance(runtime_specs, dict):
        return None
    normalizer_spec = runtime_specs.get("normalizer")
    if normalizer_spec is None:
        return None
    data = adapter.invoke_contract(
        normalizer_spec,
        {"action": BUILD_PROJECTION_CATALOG_ACTION},
        timeout=policy_store.projection_catalog_timeout_seconds(),
    )
    status = str(data.get("status", "")).strip().upper()
    if status != "OK":
        message = contract_parsing.response_error(data) or "Normalizer did not provide a projection catalog."
        raise ModuleContractError(message)
    return _validated_catalog(data.get("projection_catalog"))


def _validated_catalog(catalog: Any) -> dict[str, Any]:
    if not isinstance(catalog, dict):
        raise ModuleContractError("Normalizer provided an invalid projection_catalog.")
    if not str(catalog.get("catalog_version", "")).strip():
        raise ModuleContractError("projection_catalog.catalog_version is missing.")
    if not str(catalog.get("master_taxonomy_version", "")).strip():
        raise ModuleContractError("projection_catalog.master_taxonomy_version is missing.")
    if not isinstance(catalog.get("projections"), list):
        raise ModuleContractError("projection_catalog.projections is missing.")
    for field in _OPTIONAL_CATALOG_METADATA_FIELDS:
        if field in catalog and not str(catalog.get(field, "")).strip():
            raise ModuleContractError(f"projection_catalog.{field} is missing.")
    return catalog
