"""Shared parsers for source-authoring tool operations."""
from __future__ import annotations

from typing import Any

from ..taxonomy_sources import policy as source_policy
from . import adapter, locale_views


def find_term(master: dict[str, Any], section_id: str, term_id: str) -> dict[str, Any]:
    for item in require_list(master.get(section_id), label=section_id):
        if item.get("term_id") == term_id:
            return item
    raise ValueError(f"Master-Term nicht gefunden: {section_id}.{term_id}")


def require_projection(profiles: dict[str, Any], projection_id: str) -> dict[str, Any]:
    if projection_id not in profiles:
        raise ValueError(f"Projection nicht gefunden: {projection_id}")
    return profiles[projection_id]


def require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value


def require_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return value


def required_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()


def require_text_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste von Strings sein.")
    return [required_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)]


def package_and_locale(project_root, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    context = adapter.load_context(project_root)
    package = context["package"]
    locale = source_policy.require_locale(payload.get("locale"), label="locale")
    if locale not in set(locale_views.available_locales(package)):
        raise ValueError(f"locale ist im Source-Paket nicht vorhanden: {locale}")
    return package, locale
