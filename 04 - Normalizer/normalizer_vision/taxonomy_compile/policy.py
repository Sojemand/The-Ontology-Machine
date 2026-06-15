"""Pure source-to-flat compile helpers."""
from __future__ import annotations

from typing import Any

from ..taxonomy import upgrade_master_taxonomy_v2, upgrade_projection_payload_v2
from ..taxonomy.policy import deepcopy_json
from ..taxonomy_sources import policy as source_policy
from .types import CompiledTaxonomyAssets

_ALIAS_SECTIONS = frozenset({"document_types", "categories", "subcategories", "field_codes", "cell_codes"})
_MASTER_ID_KEYS = {"domains": "id"}


def compile_source_package(
    payload: dict[str, Any],
    *,
    projection_ids: list[str] | None = None,
    target_locale: str | None = None,
) -> CompiledTaxonomyAssets:
    release = deepcopy_json(payload["release"])
    release["available_locales"] = source_policy.canonical_locale_list(
        release.get("available_locales"),
        label="release.available_locales",
    )
    release["projection_ids"] = source_policy.canonical_projection_id_list(
        projection_ids if projection_ids is not None else release.get("projection_ids"),
        label="release.projection_ids",
    )
    runtime_locale = source_policy.require_locale(
        target_locale if target_locale is not None else release.get("default_runtime_locale"),
        label="target_locale" if target_locale is not None else "release.default_runtime_locale",
    )
    locale_payload = source_policy.materialize_locale_view(
        payload,
        locale=runtime_locale,
    )
    master = _compile_master_base(locale_payload)
    projections = {
        projection_id: _compile_projection(
            master,
            projection_id,
            locale_payload["projections"][projection_id],
        )
        for projection_id in release["projection_ids"]
    }
    release["runtime_locale"] = runtime_locale
    master["projection_templates"] = [deepcopy_json(projections[projection_id]) for projection_id in release["projection_ids"]]
    return CompiledTaxonomyAssets(
        master=upgrade_master_taxonomy_v2(master),
        projections=projections,
        release=release,
    )


def source_recipe_defaults(release: dict[str, Any], *, materialization_version: str) -> dict[str, Any]:
    return {
        "release_id": str(release.get("release_id") or "").strip(),
        "release_version": str(release.get("release_version") or "").strip(),
        "projection_ids": source_policy.canonical_projection_id_list(
            release.get("projection_ids"),
            label="release.projection_ids",
        ),
        "materialization_version": str(materialization_version).strip() or "1",
    }


def _compile_master_base(payload: dict[str, Any]) -> dict[str, Any]:
    master_core = payload["master"]["core"]
    master_text = payload["master"]["text"]
    compiled = {
        "taxonomy_id": master_core["taxonomy_id"],
        "taxonomy_version": master_core["taxonomy_version"],
        "status": master_core["status"],
        "description": master_text["description"],
        "defaults": deepcopy_json(master_core["defaults"]),
        "governance": deepcopy_json(master_core["governance"]),
        "compatibility": deepcopy_json(master_core["compatibility"]),
        "promotion_slots": deepcopy_json(master_core["promotion_slots"]),
    }
    for section_name in source_policy.MASTER_TEXT_COLLECTIONS:
        compiled[section_name] = _compile_master_collection(
            section_name,
            master_core[section_name],
            master_text[section_name],
        )
    return upgrade_master_taxonomy_v2(compiled)


def _compile_master_collection(
    section_name: str,
    core_entries: dict[str, dict[str, Any]],
    text_entries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    id_key = _MASTER_ID_KEYS.get(section_name, "code")
    compiled: list[dict[str, Any]] = []
    for item_key, core_entry in core_entries.items():
        payload = {id_key: item_key}
        text_entry = deepcopy_json(text_entries[item_key])
        if section_name in _ALIAS_SECTIONS:
            text_entry.setdefault("aliases", [])
        payload.update(text_entry)
        payload.update(deepcopy_json(core_entry))
        compiled.append(payload)
    return compiled


def _compile_projection(
    master: dict[str, Any],
    projection_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    core = payload["core"]
    text = payload["text"]
    routing_core = core["routing"]
    routing_text = text["routing"]
    lexicon = text["routing_lexicon"]
    compiled = {
        "projection_id": projection_id,
        "label": text["label"],
        "description": text["description"],
        "projection_family": core["projection_family"],
        "materialization_profile_id": core["materialization_profile_id"],
        "extends": list(core["extends"]),
        "domain_ids": list(core["domain_ids"]),
        "include_document_types": list(core["include_document_types"]),
        "include_categories": list(core["include_categories"]),
        "include_subcategories": list(core["include_subcategories"]),
        "include_field_codes": list(core["include_field_codes"]),
        "include_row_types": list(core["include_row_types"]),
        "include_cell_codes": list(core["include_cell_codes"]),
        "promotion_rules": deepcopy_json(core["promotion_rules"]),
        "compatibility": deepcopy_json(core["compatibility"]),
        "routing": {
            "when_to_use": routing_text["when_to_use"],
            "avoid_when": routing_text["avoid_when"],
            "example_document_types": list(routing_core["example_document_types"]),
            "surface_signals": {
                "text_markers": list(lexicon["text_markers"]),
                "domain_markers": deepcopy_json(lexicon["domain_markers"]),
                "section_roles": list(routing_core["section_roles"]),
                "party_roles": list(routing_core["party_roles"]),
            },
        },
    }
    return upgrade_projection_payload_v2(master, compiled)
