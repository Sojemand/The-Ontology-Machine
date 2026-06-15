"""Workflow stage for taxonomy loading, validation, and projection building."""
from __future__ import annotations

from . import policy, validation
from .promotion_rules import promotion_rules_from_fields
from .surface_signals import projection_surface_signals
from .types import (
    DEFAULT_MATERIALIZATION_PROFILE_ID,
    DEFAULT_PROJECTION_VERSION,
    JsonDict,
    PROJECTION_SECTION_SPECS,
    TaxonomyProfile,
)


def validate_master_taxonomy(data: JsonDict) -> JsonDict:
    return validation.ensure_master_required_keys(policy.upgrade_master_taxonomy_v2(data))


def build_profile_from_master(master: JsonDict, template: JsonDict) -> TaxonomyProfile:
    validated_master = _validated_master_for_profile(master)
    upgraded_template = policy.upgrade_projection_payload_v2(validated_master, template)
    return _profile_from_validated_master(validated_master, upgraded_template)


def build_profiles_from_compiled_master(
    master: JsonDict,
    projections: dict[str, JsonDict],
    projection_ids: list[str] | None = None,
) -> dict[str, TaxonomyProfile]:
    validated_master = _validated_master_for_profile(master)
    ordered_ids = list(projection_ids or projections)
    return {
        projection_id: _profile_from_validated_master(validated_master, projections[projection_id])
        for projection_id in ordered_ids
        if projection_id in projections
    }


def _validated_master_for_profile(master: JsonDict) -> JsonDict:
    profile_master = dict(master)
    profile_master["projection_templates"] = []
    return validate_master_taxonomy(profile_master)


def _profile_from_validated_master(validated_master: JsonDict, upgraded_template: JsonDict) -> TaxonomyProfile:
    return TaxonomyProfile(
        projection_id=str(upgraded_template.get("projection_id") or upgraded_template.get("id") or ""),
        label=str(upgraded_template.get("label", "")),
        description=str(upgraded_template.get("description", "")),
        master_taxonomy_id=str(upgraded_template.get("master_taxonomy_id") or validated_master.get("taxonomy_id", "normalizer_taxonomy.master")),
        master_taxonomy_version=str(upgraded_template.get("master_taxonomy_version") or validated_master.get("taxonomy_version", "")),
        domain_ids=list(upgraded_template.get("domain_ids", [])),
        projection_family=str(upgraded_template.get("projection_family", "")),
        projection_version=str(upgraded_template.get("projection_version", DEFAULT_PROJECTION_VERSION)),
        materialization_profile_id=str(upgraded_template.get("materialization_profile_id", DEFAULT_MATERIALIZATION_PROFILE_ID)),
        promotion_rules=list(upgraded_template.get("promotion_rules", [])),
        promotion_slots=_projection_promotion_slots(validated_master, upgraded_template),
        compatibility=dict(upgraded_template.get("compatibility", {})),
        projection_fingerprint=str(upgraded_template.get("projection_fingerprint") or policy.profile_fingerprint(upgraded_template)),
        surface_signals=projection_surface_signals(upgraded_template, required=False),
        document_types=validation.materialize_codes(validation.index_codes(validated_master["document_types"], "document_types"), list(upgraded_template.get("include_document_types", [])), "document_type"),
        categories=validation.materialize_codes(validation.index_codes(validated_master["categories"], "categories"), list(upgraded_template.get("include_categories", [])), "category"),
        subcategories=validation.materialize_codes(validation.index_codes(validated_master["subcategories"], "subcategories"), list(upgraded_template.get("include_subcategories", [])), "subcategory"),
        field_codes=validation.materialize_codes(validation.index_codes(validated_master["field_codes"], "field_codes"), list(upgraded_template.get("include_field_codes", [])), "field"),
        row_types=validation.materialize_codes(validation.index_codes(validated_master["row_types"], "row_types"), list(upgraded_template.get("include_row_types", [])), "row"),
        cell_codes=validation.materialize_codes(validation.index_codes(validated_master["cell_codes"], "cell_codes"), list(upgraded_template.get("include_cell_codes", [])), "cell"),
    )


def _projection_promotion_slots(master: JsonDict, projection: JsonDict) -> list[JsonDict]:
    referenced_slots = {
        str(rule.get("slot") or "").strip()
        for rule in projection.get("promotion_rules", []) or []
        if isinstance(rule, dict) and str(rule.get("slot") or "").strip()
    }
    if not referenced_slots:
        return []
    return [
        dict(slot_def)
        for slot_def in master.get("promotion_slots", []) or []
        if isinstance(slot_def, dict) and str(slot_def.get("slot") or "").strip() in referenced_slots
    ]


def build_projection_payload(master: JsonDict, payload: JsonDict) -> JsonDict:
    return policy.upgrade_projection_payload_v2(master, payload)


def find_projection_template(master: JsonDict, template_id: str) -> JsonDict:
    return validation.require_projection_template(validate_master_taxonomy(master), template_id)


def projection_payload_from_template(master: JsonDict, template_id: str) -> JsonDict:
    return build_projection_payload(master, find_projection_template(master, template_id))


def projection_payload_from_domains(
    master: JsonDict,
    *,
    projection_id: str,
    label: str,
    description: str = "",
    domain_ids: list[str] | None = None,
) -> JsonDict:
    validated_master = validate_master_taxonomy(master)
    selected_domain_ids = policy.dedupe_strings(list(domain_ids or []))
    selected_domains = set(selected_domain_ids)
    payload: JsonDict = {
        "projection_id": projection_id,
        "label": label,
        "description": description,
        "domain_ids": selected_domain_ids,
        "projection_family": "domain_selected",
        "projection_version": DEFAULT_PROJECTION_VERSION,
        "materialization_profile_id": DEFAULT_MATERIALIZATION_PROFILE_ID,
    }
    for section_key, include_key, code_key in PROJECTION_SECTION_SPECS:
        codes: list[str] = []
        for item in validated_master.get(section_key, []) or []:
            if not isinstance(item, dict):
                continue
            code = str(item.get(code_key, "")).strip()
            item_domains = {str(value).strip() for value in item.get("domains", []) or [] if str(value).strip()}
            if code and (code == "other" or not selected_domains or item_domains.intersection(selected_domains)):
                codes.append(code)
        payload[include_key] = codes
    payload["promotion_rules"] = promotion_rules_from_fields(
        [dict(item) for item in validated_master.get("field_codes", []) if isinstance(item, dict)],
        include_field_codes=list(payload.get("include_field_codes", [])),
    )
    return build_projection_payload(validated_master, payload)
