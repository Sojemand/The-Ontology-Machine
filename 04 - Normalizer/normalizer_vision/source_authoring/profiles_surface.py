"""Source-backed surface helpers for locale-aware projection authoring."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..taxonomy_sources import policy as source_policy
from ..taxonomy_sources.governance import sync_release_governance
from ..taxonomy_sources import validate_source_package_payload
from . import adapter, locale_views


def read_surface(project_root) -> dict[str, object]:
    context = adapter.load_context(project_root)
    return _surface_payload(
        context["package"],
        active_locale=locale_views.default_authoring_locale(context["package"]),
    )


def validate_surface(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    package, active_locale = _package_from_payload(context["package"], payload)
    validated = validate_source_package_payload(package)
    return _surface_payload(validated, active_locale=active_locale)


def write_surface(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    package, active_locale = _package_from_payload(context["package"], payload)
    saved = adapter.save_context(project_root, package)
    return _surface_payload(saved, active_locale=active_locale)


def _surface_payload(package: dict[str, Any], *, active_locale: str) -> dict[str, object]:
    return locale_views.clone_profiles_locale_payload(package, active_locale)


def _package_from_payload(package: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    data = _require_mapping(payload, label="normalizer.taxonomy_profiles")
    if sorted(data) != ["active_locale", "profiles"]:
        raise ValueError("normalizer.taxonomy_profiles darf nur die Felder active_locale und profiles enthalten.")
    active_locale = locale_views.active_locale(data, package)
    profiles = _require_mapping(data.get("profiles"), label="profiles")
    updated = deepcopy(package)
    collected_profiles: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for projection_id, item in profiles.items():
        entry = _require_mapping(item, label=f"profiles.{projection_id}")
        actual_id = _require_text(entry.get("projection_id"), label=f"profiles.{projection_id}.projection_id")
        if actual_id != projection_id:
            raise ValueError(f"profiles.{projection_id}.projection_id muss '{projection_id}' sein.")
        existing_entry = updated["projections"].get(actual_id) or updated["projections"].get(projection_id) or {"texts": {}}
        current_text = _require_mapping(entry.get("text"), label=f"profiles.{projection_id}.text")
        all_texts: dict[str, dict[str, Any]] = {}
        for locale in locale_views.available_locales(updated):
            existing_locale_text = existing_entry.get("texts", {}).get(locale)
            if locale == active_locale:
                all_texts[locale] = current_text
            elif isinstance(existing_locale_text, dict):
                all_texts[locale] = deepcopy(existing_locale_text)
            else:
                all_texts[locale] = deepcopy(current_text)
        collected_profiles[projection_id] = {
            "core": _require_mapping(entry.get("core"), label=f"profiles.{projection_id}.core"),
            "texts": all_texts,
        }
        ordered_ids.append(projection_id)
    canonical_projection_ids = source_policy.canonical_projection_id_list(
        ordered_ids,
        label="profiles",
    )
    if ordered_ids != canonical_projection_ids:
        raise ValueError("profiles muessen kanonisch nach projection_id sortiert sein.")
    updated["projections"] = {
        projection_id: collected_profiles[projection_id]
        for projection_id in canonical_projection_ids
    }
    updated["release"]["projection_ids"] = canonical_projection_ids
    updated["release"] = sync_release_governance(
        updated["release"],
        glossary_locales=sorted(updated.get("glossaries", {})),
    )
    return updated, active_locale


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def _require_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()
