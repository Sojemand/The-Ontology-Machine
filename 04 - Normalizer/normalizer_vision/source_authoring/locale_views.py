"""Helpers for English control-language authoring views on top of the source package."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def available_locales(package: dict[str, Any]) -> list[str]:
    return list(package["release"]["available_locales"])


def default_authoring_locale(package: dict[str, Any]) -> str:
    return str(package["release"]["default_authoring_locale"])


def default_runtime_locale(package: dict[str, Any]) -> str:
    return str(package["release"]["default_runtime_locale"])


def active_locale(payload: dict[str, Any], package: dict[str, Any]) -> str:
    locale = str(payload.get("active_locale") or "").strip() or default_authoring_locale(package)
    if locale not in set(available_locales(package)):
        raise ValueError(f"Unbekannte Locale: {locale}")
    return locale


def master_text(package: dict[str, Any], locale: str) -> dict[str, Any]:
    return package["master"]["texts"][locale]


def glossary(package: dict[str, Any], locale: str) -> dict[str, Any]:
    return package.get("glossaries", {}).get(locale, {"glossary": {}})


def projection_text(package: dict[str, Any], projection_id: str, locale: str) -> dict[str, Any]:
    return package["projections"][projection_id]["texts"][locale]


def clone_master_locale_payload(package: dict[str, Any], locale: str) -> dict[str, Any]:
    text_payload = master_text(package, locale)
    payload: dict[str, Any] = {"active_locale": locale, "description": text_payload["description"]}
    for section_name in package["master"]["core"]:
        section_core = package["master"]["core"].get(section_name)
        section_text = text_payload.get(section_name)
        if not isinstance(section_core, dict) or not isinstance(section_text, dict):
            continue
        payload[section_name] = [
            {
                "term_id": term_id,
                "core": deepcopy(core_entry),
                "text": deepcopy(section_text[term_id]),
            }
            for term_id, core_entry in section_core.items()
        ]
    return payload


def clone_profiles_locale_payload(package: dict[str, Any], locale: str) -> dict[str, Any]:
    return {
        "active_locale": locale,
        "profiles": {
            projection_id: {
                "projection_id": projection_id,
                "core": deepcopy(package["projections"][projection_id]["core"]),
                "text": deepcopy(projection_text(package, projection_id, locale)),
            }
            for projection_id in package["release"]["projection_ids"]
        },
    }


def clone_glossary_locale_payload(package: dict[str, Any], locale: str) -> dict[str, Any]:
    glossary_payload = glossary(package, locale)
    return {
        "active_locale": locale,
        "entries": [
            {"english_term": term, **deepcopy(item)}
            for term, item in glossary_payload.get("glossary", {}).items()
        ],
    }
