"""Semantic fail-closed validation for locale-aware taxonomy source packages."""
from __future__ import annotations

from typing import Any

from ..runtime_semantic_assets.semantic_policy import _COMMON_SECTION_ROLES
from ..taxonomy.surface_signals import projection_surface_signals
from ..taxonomy.promotion_rules import validate_promotion_rules
from ..taxonomy.types import PROJECTION_SECTION_SPECS, normalize_lookup_token
from . import policy
from .semantic_binding_validation import validate_semantic_bindings
from .semantic_validation_aliases import validate_alias_collisions

_ALIAS_SECTIONS = frozenset({"document_types", "categories", "subcategories", "field_codes", "row_types", "cell_codes"})
_ALLOWED_SECTION_ROLES = set(_COMMON_SECTION_ROLES) | {"form"}
_REQUIRED_TEXT_FIELDS = {
    "domains": ("label", "description"),
    "document_types": ("label", "description"),
    "categories": ("label", "description"),
    "subcategories": ("label", "description"),
    "field_codes": ("label", "description"),
    "row_types": ("label", "description"),
    "cell_codes": ("label", "description"),
    "entity_types": ("label", "description"),
    "role_types": ("label",),
    "relation_types": ("label",),
}
_ALLOWED_VALUE_TYPES = frozenset({"string", "date_or_string", "number_or_string", "number_or_money_string"})


def validate_source_package_semantics(payload: dict[str, Any]) -> None:
    master_core = payload["master"]["core"]
    master_texts = payload["master"]["texts"]
    available_locales = list(payload["release"]["available_locales"])
    indexes = _build_indexes(master_core)
    for locale in available_locales:
        _validate_master_text(master_core, master_texts[locale], locale=locale)
    _validate_master_core(master_core, indexes)
    _validate_projections(payload["release"], payload["projections"], indexes, available_locales)


def _build_indexes(master_core: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "domains": set(master_core["domains"]),
        "document_types": set(master_core["document_types"]),
        "categories": set(master_core["categories"]),
        "subcategories": set(master_core["subcategories"]),
        "field_codes": set(master_core["field_codes"]),
        "row_types": set(master_core["row_types"]),
        "cell_codes": set(master_core["cell_codes"]),
        "entity_types": set(master_core["entity_types"]),
        "role_types": set(master_core["role_types"]),
        "promotion_slots": {
            policy.require_text(item.get("slot"), label="master.core.promotion_slots[].slot")
            for item in master_core["promotion_slots"]
        },
    }


def _validate_master_text(master_core: dict[str, Any], master_text: dict[str, Any], *, locale: str) -> None:
    for section_name, required_fields in _REQUIRED_TEXT_FIELDS.items():
        core_keys = set(master_core[section_name])
        text_keys = set(master_text[section_name])
        if core_keys != text_keys:
            missing = sorted(core_keys - text_keys)
            extra = sorted(text_keys - core_keys)
            parts = [f"fehlend: {', '.join(missing)}" for missing in [missing] if missing]
            parts.extend(f"extra: {', '.join(extra)}" for extra in [extra] if extra)
            raise ValueError(f"master.text.{locale}.{section_name} passt nicht zum Core ({'; '.join(parts)})")
        if section_name in _ALIAS_SECTIONS:
            validate_alias_collisions(section_name, master_text[section_name], locale=locale)
        for item_key, entry in master_text[section_name].items():
            for field_name in required_fields:
                policy.require_text(
                    entry.get(field_name),
                    label=f"master.text.{locale}.{section_name}.{item_key}.{field_name}",
                )


def _validate_master_core(master_core: dict[str, Any], indexes: dict[str, set[str]]) -> None:
    _validate_domain_refs("master.core.document_types", master_core["document_types"], indexes["domains"])
    _validate_domain_refs("master.core.categories", master_core["categories"], indexes["domains"])
    _validate_domain_refs("master.core.subcategories", master_core["subcategories"], indexes["domains"])
    _validate_domain_refs("master.core.field_codes", master_core["field_codes"], indexes["domains"])
    _validate_domain_refs("master.core.row_types", master_core["row_types"], indexes["domains"])
    _validate_domain_refs("master.core.cell_codes", master_core["cell_codes"], indexes["domains"])
    _validate_refs("master.core.document_types", "allowed_categories", master_core["document_types"], indexes["categories"])
    _validate_refs("master.core.document_types", "allowed_subcategories", master_core["document_types"], indexes["subcategories"])
    _validate_refs("master.core.row_types", "recommended_cell_codes", master_core["row_types"], indexes["cell_codes"])
    for item_key, entry in master_core["subcategories"].items():
        parent = policy.require_text(
            entry.get("parent_category"),
            label=f"master.core.subcategories.{item_key}.parent_category",
        )
        if parent not in indexes["categories"]:
            raise ValueError(f"master.core.subcategories.{item_key}.parent_category referenziert unbekannte category: {parent}")
    _validate_value_types("master.core.field_codes", master_core["field_codes"])
    _validate_value_types("master.core.cell_codes", master_core["cell_codes"])
    _validate_value_types("master.core.promotion_slots", {item["slot"]: item for item in master_core["promotion_slots"]})
    validate_semantic_bindings(master_core, indexes)


def _validate_projections(
    release: dict[str, Any],
    projections: dict[str, Any],
    indexes: dict[str, set[str]],
    available_locales: list[str],
) -> None:
    projection_ids = set(release["projection_ids"])
    for projection_id, parts in projections.items():
        core = parts["core"]
        _validate_known_list(f"{projection_id}.core.domain_ids", core["domain_ids"], indexes["domains"])
        _validate_known_list(f"{projection_id}.core.extends", core["extends"], projection_ids - {projection_id})
        for _, include_key, _ in PROJECTION_SECTION_SPECS:
            _validate_known_list(
                f"{projection_id}.core.{include_key}",
                core[include_key],
                indexes[include_key.removeprefix("include_")],
            )
        examples = policy.require_string_list(
            core["routing"]["example_document_types"],
            label=f"{projection_id}.core.routing.example_document_types",
        )
        _validate_known_list(f"{projection_id}.core.routing.example_document_types", examples, indexes["document_types"])
        if not set(examples).issubset(set(core["include_document_types"])):
            raise ValueError(f"{projection_id}.core.routing.example_document_types muessen in include_document_types enthalten sein.")
        _validate_role_tokens(f"{projection_id}.core.routing.party_roles", core["routing"]["party_roles"])
        _validate_known_list(f"{projection_id}.core.routing.section_roles", core["routing"]["section_roles"], _ALLOWED_SECTION_ROLES)
        if not core["domain_ids"] or not core["include_document_types"] or not examples:
            raise ValueError(f"{projection_id} hat keine tragfaehige Fachabdeckung.")
        coverage = sum(len(core[key]) for _, key, _ in PROJECTION_SECTION_SPECS)
        if coverage <= len(core["include_document_types"]):
            raise ValueError(f"{projection_id} hat keine tragfaehige Fachabdeckung.")
        validate_promotion_rules(
            {
                "promotion_slots": [{"slot": slot} for slot in indexes["promotion_slots"]],
                "field_codes": {key: {} for key in indexes["field_codes"]},
                "cell_codes": {key: {} for key in indexes["cell_codes"]},
            },
            core,
            label=f"{projection_id}.core",
            strict_source_paths=core.get("projection_family") == "custom",
        )
        for locale in available_locales:
            text = parts["texts"][locale]
            if not text["routing_lexicon"]["text_markers"] and not any(text["routing_lexicon"]["domain_markers"].values()):
                raise ValueError(f"{projection_id}.text.{locale}.routing_lexicon darf nicht leer sein.")
            projection_surface_signals(
                {
                    "projection_id": projection_id,
                    "domain_ids": list(core["domain_ids"]),
                    "routing": {
                        "surface_signals": {
                            "text_markers": list(text["routing_lexicon"]["text_markers"]),
                            "domain_markers": dict(text["routing_lexicon"]["domain_markers"]),
                            "section_roles": list(core["routing"]["section_roles"]),
                            "party_roles": list(core["routing"]["party_roles"]),
                        }
                    },
                },
                required=True,
            )


def _validate_domain_refs(label: str, payload: dict[str, Any], known_domains: set[str]) -> None:
    _validate_refs(label, "domains", payload, known_domains)


def _validate_refs(label: str, field_name: str, payload: dict[str, Any], known: set[str]) -> None:
    for item_key, entry in payload.items():
        _validate_known_list(f"{label}.{item_key}.{field_name}", entry.get(field_name, []), known)


def _validate_known_list(label: str, values: list[str], known: set[str]) -> None:
    unknown = sorted(value for value in values if value not in known)
    if unknown:
        raise ValueError(f"{label} referenziert unbekannte Werte: {', '.join(unknown)}")


def _validate_role_tokens(label: str, values: list[str]) -> None:
    invalid = sorted(value for value in values if normalize_lookup_token(value) != value)
    if invalid:
        raise ValueError(f"{label} enthaelt ungueltige Rollen-Keys: {', '.join(invalid)}")


def _validate_value_types(label: str, payload: dict[str, Any]) -> None:
    for item_key, entry in payload.items():
        value_type = policy.require_text(entry.get("value_type"), label=f"{label}.{item_key}.value_type")
        if value_type not in _ALLOWED_VALUE_TYPES:
            raise ValueError(f"{label}.{item_key}.value_type ist ungueltig: {value_type}")
