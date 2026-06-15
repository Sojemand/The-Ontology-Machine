"""Source-backed surface helpers for locale-aware release authoring."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..taxonomy_sources import policy as source_policy
from ..taxonomy_sources.governance import sync_release_governance
from ..taxonomy_sources import validate_source_package_payload
from . import adapter

_SURFACE_FIELDS = (
    "release_id",
    "release_version",
    "available_locales",
    "default_authoring_locale",
    "default_runtime_locale",
    "projection_ids",
)


def read_surface(project_root) -> dict[str, object]:
    context = adapter.load_context(project_root)
    return _surface_payload(context["package"])


def validate_surface(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    package = _package_from_payload(context["package"], payload)
    validated = validate_source_package_payload(package)
    return _surface_payload(validated)


def write_surface(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    package = _package_from_payload(context["package"], payload)
    saved = adapter.save_context(project_root, package)
    return _surface_payload(saved)


def _surface_payload(package: dict[str, Any]) -> dict[str, object]:
    release = package["release"]
    return {
        "release_id": release["release_id"],
        "release_version": release["release_version"],
        "available_locales": list(release["available_locales"]),
        "default_authoring_locale": release["default_authoring_locale"],
        "default_runtime_locale": release["default_runtime_locale"],
        "projection_ids": list(release["projection_ids"]),
    }


def _package_from_payload(
    package: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    data = _require_mapping(payload, label="normalizer.semantic_release_authoring")
    unknown = sorted(set(data) - set(_SURFACE_FIELDS))
    if unknown:
        raise ValueError(f"normalizer.semantic_release_authoring enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [field_name for field_name in _SURFACE_FIELDS if field_name not in data]
    if missing:
        raise ValueError(f"normalizer.semantic_release_authoring enthaelt fehlende Felder: {', '.join(missing)}")
    selected_ids = source_policy.require_projection_id_list(
        data.get("projection_ids"),
        label="projection_ids",
    )
    canonical_projection_ids = source_policy.canonical_projection_id_list(
        data.get("projection_ids"),
        label="projection_ids",
    )
    if selected_ids != canonical_projection_ids:
        raise ValueError("projection_ids muss kanonisch nach projection_id sortiert sein.")
    known_ids = set(package["projections"])
    unknown_ids = sorted(set(selected_ids) - known_ids)
    if unknown_ids:
        raise ValueError(f"Unbekannte Projection IDs: {', '.join(unknown_ids)}")
    updated = deepcopy(package)
    updated["release"]["release_id"] = source_policy.require_source_id(data.get("release_id"), label="release_id")
    updated["release"]["release_version"] = _require_text(data.get("release_version"), label="release_version")
    updated["release"]["available_locales"] = source_policy.canonical_locale_list(
        data.get("available_locales"),
        label="available_locales",
    )
    updated["release"]["default_authoring_locale"] = source_policy.require_locale(
        data.get("default_authoring_locale"),
        label="default_authoring_locale",
    )
    updated["release"]["default_runtime_locale"] = source_policy.require_locale(
        data.get("default_runtime_locale"),
        label="default_runtime_locale",
    )
    updated["release"]["projection_ids"] = canonical_projection_ids
    updated["projections"] = {
        projection_id: deepcopy(package["projections"][projection_id])
        for projection_id in canonical_projection_ids
    }
    updated["release"] = sync_release_governance(
        updated["release"],
        glossary_locales=sorted(updated.get("glossaries", {})),
    )
    return updated


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def _require_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()
