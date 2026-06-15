"""Source-backed helpers for English control glossary authoring."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

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
    return locale_views.clone_glossary_locale_payload(package, active_locale)


def _package_from_payload(package: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    data = _require_mapping(payload, label="normalizer.translation_glossary")
    if sorted(data) != ["active_locale", "entries"]:
        raise ValueError("normalizer.translation_glossary darf nur die Felder active_locale und entries enthalten.")
    active_locale = locale_views.active_locale(data, package)
    updated = deepcopy(package)
    entries_payload: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for index, item in enumerate(_require_list(data.get("entries"), label="entries")):
        entry = _require_mapping(item, label=f"entries[{index}]")
        english_term = _require_text(entry.get("english_term"), label=f"entries[{index}].english_term")
        if english_term in seen:
            raise ValueError(f"entries enthaelt doppelte english_term: {english_term}")
        seen.add(english_term)
        entries_payload[english_term] = {
            "canonical": _require_text(entry.get("canonical"), label=f"entries[{index}].canonical"),
            "aliases": _require_text_list(entry.get("aliases"), label=f"entries[{index}].aliases"),
        }
    updated.setdefault("glossaries", {})
    if entries_payload:
        updated["glossaries"][active_locale] = {"glossary": entries_payload}
    else:
        updated["glossaries"].pop(active_locale, None)
    updated["release"] = sync_release_governance(
        updated["release"],
        glossary_locales=sorted(updated.get("glossaries", {})),
    )
    return updated, active_locale


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def _require_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return value


def _require_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()


def _require_text_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste von Strings sein.")
    return [_require_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
