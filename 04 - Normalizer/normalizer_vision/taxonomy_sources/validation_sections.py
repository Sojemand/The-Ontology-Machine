"""Section-level validation for source packages."""
from __future__ import annotations

from typing import Any

from . import policy
from .validation_keys import MASTER_CORE_KEYS, MASTER_TEXT_KEYS, PROJECTION_CORE_KEYS, PROJECTION_TEXT_KEYS


def validate_locale_mapping_keys(payload: dict[str, Any], *, label: str, available_locales: list[str], require_all: bool) -> None:
    unknown = sorted(locale for locale in payload if locale not in available_locales)
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Locales: {', '.join(unknown)}")
    if require_all:
        missing = [locale for locale in available_locales if locale not in payload]
        if missing:
            raise ValueError(f"{label} enthaelt fehlende Locales: {', '.join(missing)}")


def validate_master_core(payload: dict[str, Any]) -> None:
    policy.require_exact_keys(payload, label="master.core", expected=MASTER_CORE_KEYS)
    for section_name in policy.MASTER_TEXT_COLLECTIONS:
        collection = policy.require_mapping(payload.get(section_name), label=f"master.core.{section_name}")
        for item_key, item in collection.items():
            entry = policy.require_mapping(item, label=f"master.core.{section_name}.{item_key}")
            policy.reject_text_keys(entry, label=f"master.core.{section_name}.{item_key}")
            for authoring_key in ("promotion_slot", "promotion_cardinality", "query_role", "display_rank"):
                if authoring_key in entry:
                    raise ValueError(f"master.core.{section_name}.{item_key}.{authoring_key} ist nicht im Core-Source erlaubt.")
    for field_name in ("defaults", "governance", "compatibility"):
        policy.reject_text_keys(payload.get(field_name), label=f"master.core.{field_name}")


def validate_master_text(payload: dict[str, Any], *, locale: str) -> None:
    policy.require_exact_keys(payload, label=f"master.text.{locale}", expected=MASTER_TEXT_KEYS)
    policy.require_text(payload.get("description"), label=f"master.text.{locale}.description")
    for collection_name in policy.MASTER_TEXT_COLLECTIONS:
        policy.validate_text_collection(payload.get(collection_name), label=f"master.text.{locale}.{collection_name}")


def validate_glossary(payload: dict[str, Any], *, locale: str) -> None:
    policy.require_exact_keys(payload, label=f"translation_glossary.{locale}", expected=("glossary",))
    glossary = policy.require_mapping(payload.get("glossary"), label=f"translation_glossary.{locale}.glossary")
    for term, item in glossary.items():
        entry = policy.require_mapping(item, label=f"translation_glossary.{locale}.glossary.{term}")
        policy.require_exact_keys(entry, label=f"translation_glossary.{locale}.glossary.{term}", expected=("canonical", "aliases"))
        policy.require_text(entry.get("canonical"), label=f"translation_glossary.{locale}.glossary.{term}.canonical")
        policy.require_string_list(entry.get("aliases"), label=f"translation_glossary.{locale}.glossary.{term}.aliases")


def validate_projection_core(payload: dict[str, Any], *, projection_id: str) -> None:
    policy.require_exact_keys(payload, label=f"{projection_id}.core", expected=PROJECTION_CORE_KEYS)
    if policy.require_text(payload.get("projection_id"), label=f"{projection_id}.core.projection_id") != projection_id:
        raise ValueError(f"{projection_id}.core.projection_id passt nicht zum Dateinamen.")
    policy.reject_text_keys(payload, label=f"{projection_id}.core")
    routing = policy.require_mapping(payload.get("routing"), label=f"{projection_id}.core.routing")
    policy.require_exact_keys(routing, label=f"{projection_id}.core.routing", expected=("example_document_types", "section_roles", "party_roles"))
    policy.require_string_list(routing.get("example_document_types"), label=f"{projection_id}.core.routing.example_document_types")
    policy.require_string_list(routing.get("section_roles"), label=f"{projection_id}.core.routing.section_roles")
    policy.require_string_list(routing.get("party_roles"), label=f"{projection_id}.core.routing.party_roles")


def validate_projection_text(payload: dict[str, Any], *, locale: str) -> None:
    policy.require_exact_keys(payload, label=f"projection.text.{locale}", expected=PROJECTION_TEXT_KEYS)
    policy.require_text(payload.get("label"), label=f"projection.text.{locale}.label")
    policy.require_text(payload.get("description"), label=f"projection.text.{locale}.description")
    routing = policy.require_mapping(payload.get("routing"), label=f"projection.text.{locale}.routing")
    policy.require_exact_keys(routing, label=f"projection.text.{locale}.routing", expected=("when_to_use", "avoid_when"))
    policy.require_text(routing.get("when_to_use"), label=f"projection.text.{locale}.routing.when_to_use")
    policy.require_text(routing.get("avoid_when"), label=f"projection.text.{locale}.routing.avoid_when")
    lexicon = policy.require_mapping(payload.get("routing_lexicon"), label=f"projection.text.{locale}.routing_lexicon")
    policy.require_exact_keys(lexicon, label=f"projection.text.{locale}.routing_lexicon", expected=("text_markers", "domain_markers"))
    policy.require_string_list(lexicon.get("text_markers"), label=f"projection.text.{locale}.routing_lexicon.text_markers")
    domain_markers = policy.require_mapping(lexicon.get("domain_markers"), label=f"projection.text.{locale}.routing_lexicon.domain_markers")
    for domain_id, markers in domain_markers.items():
        policy.require_string_list(markers, label=f"projection.text.{locale}.routing_lexicon.domain_markers.{domain_id}")
