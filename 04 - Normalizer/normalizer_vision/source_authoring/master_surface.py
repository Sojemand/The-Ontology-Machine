"""Source-backed surface helpers for the locale-aware taxonomy master."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..taxonomy_sources import policy as source_policy
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
    return locale_views.clone_master_locale_payload(package, active_locale)


def _package_from_payload(package: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    expected = {"active_locale", "description", *source_policy.MASTER_TEXT_COLLECTIONS}
    unknown = sorted(set(payload) - expected)
    if unknown:
        raise ValueError(f"normalizer.taxonomy_master enthaelt unbekannte Felder: {', '.join(unknown)}")
    active_locale = locale_views.active_locale(payload, package)
    description = _require_text(payload.get("description"), label="description")
    updated = deepcopy(package)
    updated["master"]["texts"][active_locale]["description"] = description
    for section_name in source_policy.MASTER_TEXT_COLLECTIONS:
        items = _require_list(payload.get(section_name), label=section_name)
        core_items: dict[str, dict[str, Any]] = {}
        current_locale_texts: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        for index, item in enumerate(items):
            entry = _require_mapping(item, label=f"{section_name}[{index}]")
            term_id = _require_text(entry.get("term_id"), label=f"{section_name}[{index}].term_id")
            if term_id in seen:
                raise ValueError(f"{section_name} enthaelt doppelte term_id: {term_id}")
            seen.add(term_id)
            core_items[term_id] = _require_mapping(entry.get("core"), label=f"{section_name}[{index}].core")
            current_locale_texts[term_id] = _require_mapping(entry.get("text"), label=f"{section_name}[{index}].text")
        updated["master"]["core"][section_name] = core_items
        for locale in locale_views.available_locales(updated):
            existing_locale_texts = updated["master"]["texts"][locale][section_name]
            if locale == active_locale:
                updated["master"]["texts"][locale][section_name] = current_locale_texts
            else:
                updated["master"]["texts"][locale][section_name] = _sync_other_locale_terms(
                    current_locale_texts,
                    existing_locale_texts,
                )
    return updated, active_locale


def _sync_other_locale_terms(
    current_locale_texts: dict[str, dict[str, Any]],
    existing_locale_texts: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    synced: dict[str, dict[str, Any]] = {}
    for term_id, current_text in current_locale_texts.items():
        if term_id in existing_locale_texts:
            synced[term_id] = deepcopy(existing_locale_texts[term_id])
        else:
            synced[term_id] = deepcopy(current_text)
    return synced


def _require_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return value


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def _require_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()
