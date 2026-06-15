"""Validation helpers and structural rules for taxonomy source packages."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from . import locale_policy

MASTER_TEXT_COLLECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
    "entity_types",
    "role_types",
    "relation_types",
)
TEXT_ENTRY_FIELDS = frozenset({"label", "description", "aliases"})
CORE_TEXT_KEYS = frozenset(
    {
        "label",
        "description",
        "aliases",
        "when_to_use",
        "avoid_when",
        "text_markers",
        "domain_markers",
        "routing_lexicon",
    }
)
CONTROL_LOCALE = locale_policy.CONTROL_LOCALE
SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._][a-z0-9]+)*$")
MAX_SOURCE_ID_LENGTH = 120


def require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein Objekt sein.")
    return value

def require_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} muss ein nicht-leerer String sein.")
    return value.strip()


def require_source_id(value: Any, *, label: str) -> str:
    text = require_text(value, label=label)
    if len(text) > MAX_SOURCE_ID_LENGTH or not SOURCE_ID_PATTERN.fullmatch(text):
        raise ValueError(f"{label} muss eine maschinenlesbare Source-ID ohne Pfadzeichen sein.")
    return text

def require_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste von Strings sein.")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}[{index}] muss ein nicht-leerer String sein.")
        result.append(item.strip())
    return result


def require_projection_id_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste von Projection-IDs sein.")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        projection_id = require_source_id(item, label=f"{label}[{index}]")
        key = projection_id.casefold()
        if key in seen:
            raise ValueError(f"{label} enthaelt doppelte Projection-ID: {projection_id}")
        seen.add(key)
        result.append(projection_id)
    return result


def require_locale(value: Any, *, label: str) -> str:
    return locale_policy.require_locale(value, label=label, require_text=require_text)


def require_locale_list(value: Any, *, label: str) -> list[str]:
    return locale_policy.require_locale_list(value, label=label, require_text=require_text)


def canonical_locale_list(value: Any, *, label: str) -> list[str]:
    return locale_policy.canonical_locale_list(value, label=label, require_text=require_text)


def canonical_projection_id_list(value: Any, *, label: str) -> list[str]:
    return sorted(
        require_projection_id_list(value, label=label),
        key=lambda item: (item.casefold(), item),
    )


def require_exact_keys(payload: dict[str, Any], *, label: str, expected: tuple[str, ...]) -> None:
    unknown = sorted(set(payload) - set(expected))
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    missing = [key for key in expected if key not in payload]
    if missing:
        raise ValueError(f"{label} enthaelt fehlende Felder: {', '.join(missing)}")


def optional_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    return require_mapping(value, label=label)


def reject_text_keys(value: Any, *, label: str) -> None:
    for path, key in iter_dict_keys(value, label=label):
        if key in CORE_TEXT_KEYS:
            raise ValueError(f"{path} darf nicht im Core-Source liegen.")


def iter_dict_keys(value: Any, *, label: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def _walk(current: Any, path: str) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                child_path = f"{path}.{key}"
                found.append((child_path, str(key)))
                _walk(child, child_path)
            return
        if isinstance(current, list):
            for index, child in enumerate(current):
                _walk(child, f"{path}[{index}]")

    _walk(value, label)
    return found


def validate_text_collection(payload: Any, *, label: str) -> dict[str, dict[str, Any]]:
    collection = require_mapping(payload, label=label)
    for item_key, item in collection.items():
        entry = require_mapping(item, label=f"{label}.{item_key}")
        unknown = sorted(set(entry) - TEXT_ENTRY_FIELDS)
        if unknown:
            raise ValueError(f"{label}.{item_key} enthaelt Core-Felder: {', '.join(unknown)}")
        if "label" in entry:
            require_text(entry.get("label"), label=f"{label}.{item_key}.label")
        if "description" in entry:
            require_text(entry.get("description"), label=f"{label}.{item_key}.description")
        if "aliases" in entry:
            require_string_list(entry.get("aliases"), label=f"{label}.{item_key}.aliases")
    return collection


def materialize_locale_view(payload: dict[str, Any], *, locale: str) -> dict[str, Any]:
    release = require_mapping(payload.get("release"), label="release")
    available_locales = require_locale_list(
        release.get("available_locales"),
        label="release.available_locales",
    )
    target_locale = require_locale(locale, label="locale")
    if target_locale not in available_locales:
        raise ValueError(f"Locale nicht im Source-Paket vorhanden: {target_locale}")
    master = require_mapping(payload.get("master"), label="master")
    master_core = require_mapping(master.get("core"), label="master.core")
    master_texts = require_mapping(master.get("texts"), label="master.texts")
    glossaries = optional_mapping(payload.get("glossaries"), label="glossaries")
    projections = require_mapping(payload.get("projections"), label="projections")
    materialized_projections: dict[str, dict[str, Any]] = {}
    for projection_id, parts in projections.items():
        projection_parts = require_mapping(parts, label=f"projections.{projection_id}")
        text_payloads = require_mapping(
            projection_parts.get("texts"),
            label=f"projections.{projection_id}.texts",
        )
        materialized_projections[projection_id] = {
            "core": deepcopy(require_mapping(projection_parts.get("core"), label=f"{projection_id}.core")),
            "text": deepcopy(
                require_mapping(
                    text_payloads.get(target_locale),
                    label=f"{projection_id}.texts.{target_locale}",
                )
            ),
        }
    glossary = deepcopy(glossaries.get(target_locale) or {"glossary": {}})
    return {
        "release": deepcopy(release),
        "master": {
            "core": deepcopy(master_core),
            "text": deepcopy(
                require_mapping(
                    master_texts.get(target_locale),
                    label=f"master.texts.{target_locale}",
                )
            ),
        },
        "glossary": glossary,
        "projections": materialized_projections,
    }
