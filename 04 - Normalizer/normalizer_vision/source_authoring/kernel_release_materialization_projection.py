from __future__ import annotations

from typing import Any, Mapping

from ..semantic_release.kernel_candidate import stable_hash
from ..taxonomy import upgrade_projection_payload_v2
from .kernel_release_materialization_base import (
    DEFAULT_CUSTOM_RELEASE_VERSION,
    master_fields,
    mapping,
    require_text,
    taxonomy_fallback_domains,
    text_list,
)
from .promotion_rules import promotion_rules_from_fields

DEFAULT_CUSTOM_PROJECTION_VERSION = "v1"


def projection_payload(*, projection_ref: Mapping[str, Any], precursor: Mapping[str, Any], base_release: Mapping[str, Any]) -> dict[str, Any]:
    projection_id = require_text(projection_ref.get("projection_id"), "projection_ref.projection_id")
    source_projection = mapping(projection_ref, "projection_payload")
    master = mapping(base_release, "master_taxonomy")
    if source_projection:
        return _source_projection_payload(
            projection_id=projection_id,
            projection_ref=projection_ref,
            precursor=precursor,
            base_release=base_release,
            source_projection=source_projection,
            master=master,
        )
    return _precursor_projection_payload(
        projection_id=projection_id,
        projection_ref=projection_ref,
        precursor=precursor,
        base_release=base_release,
        master=master,
    )


def written_projection_refs(projections: list[Mapping[str, Any]], projection_refs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    source_by_id = {str(item.get("projection_id") or ""): item for item in projection_refs}
    return [
        {
            "projection_id": str(projection.get("projection_id") or ""),
            "projection_fingerprint": str(projection.get("projection_fingerprint") or source_by_id.get(str(projection.get("projection_id") or ""), {}).get("projection_fingerprint") or ""),
            "included_taxonomy_codes": list(source_by_id.get(str(projection.get("projection_id") or ""), {}).get("included_taxonomy_codes") or []),
        }
        for projection in projections
    ]


def _source_projection_payload(
    *,
    projection_id: str,
    projection_ref: Mapping[str, Any],
    precursor: Mapping[str, Any],
    base_release: Mapping[str, Any],
    source_projection: Mapping[str, Any],
    master: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(source_projection)
    payload["projection_id"] = projection_id
    payload["master_taxonomy_id"] = str(base_release.get("master_taxonomy_id") or payload.get("master_taxonomy_id") or "")
    payload["master_taxonomy_version"] = str(base_release.get("master_taxonomy_version") or payload.get("master_taxonomy_version") or "")
    payload["projection_version"] = str(payload.get("projection_version") or projection_ref.get("projection_version") or precursor.get("projection_version") or DEFAULT_CUSTOM_PROJECTION_VERSION)
    payload["projection_fingerprint"] = str(projection_ref.get("projection_fingerprint") or payload.get("projection_fingerprint") or stable_hash(repr(sorted(dict(precursor).items()))))
    payload.setdefault("projection_family", "custom")
    payload.setdefault("extends", [])
    payload.setdefault("materialization_profile_id", "document_entities.v1")
    payload.setdefault("compatibility", {})
    payload.setdefault("promotion_rules", projection_promotion_rules(master, precursor, payload))
    return upgrade_projection_payload_v2(master, payload)


def _precursor_projection_payload(
    *,
    projection_id: str,
    projection_ref: Mapping[str, Any],
    precursor: Mapping[str, Any],
    base_release: Mapping[str, Any],
    master: Mapping[str, Any],
) -> dict[str, Any]:
    projection_version = str(projection_ref.get("projection_version") or precursor.get("projection_version") or DEFAULT_CUSTOM_PROJECTION_VERSION)
    domain_ids = text_list(precursor.get("domain_ids")) or taxonomy_fallback_domains(base_release)
    routing = mapping(precursor, "routing")
    example_types = text_list(routing.get("example_document_types")) or text_list(precursor.get("include_document_types")) or ["other"]
    section_roles = text_list(routing.get("section_roles")) or ["body", "other"]
    party_roles = text_list(routing.get("party_roles")) or ["other"]
    lexicon = mapping(precursor, "routing_lexicon")
    payload = {
        "projection_id": projection_id,
        "label": str(precursor.get("label") or projection_id.replace(".", " ").title()).strip(),
        "description": str(precursor.get("description") or f"Custom projection {projection_id}.").strip(),
        "master_taxonomy_id": str(base_release.get("master_taxonomy_id") or ""),
        "master_taxonomy_version": str(base_release.get("master_taxonomy_version") or ""),
        "domain_ids": domain_ids,
        "projection_family": "custom",
        "projection_version": projection_version,
        "projection_fingerprint": str(projection_ref.get("projection_fingerprint") or stable_hash(repr(sorted(dict(precursor).items())))),
        "extends": [],
        "materialization_profile_id": "document_entities.v1",
        "compatibility": {},
        "promotion_rules": projection_promotion_rules(master, precursor),
        "include_document_types": text_list(precursor.get("include_document_types")) or example_types,
        "include_categories": text_list(precursor.get("include_categories")) or ["other"],
        "include_subcategories": text_list(precursor.get("include_subcategories")) or ["other"],
        "include_field_codes": text_list(precursor.get("include_field_codes")) or ["other"],
        "include_row_types": text_list(precursor.get("include_row_types")) or ["other"],
        "include_cell_codes": text_list(precursor.get("include_cell_codes")) or ["other"],
        "routing": _routing_payload(projection_id, routing, precursor, lexicon, domain_ids, section_roles, party_roles, example_types),
    }
    return upgrade_projection_payload_v2(master, payload)


def projection_promotion_rules(
    master: Mapping[str, Any],
    precursor: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    include_field_codes = text_list((payload or precursor).get("include_field_codes"))
    if not include_field_codes:
        include_field_codes = text_list(precursor.get("include_field_codes"))
    return promotion_rules_from_fields(
        master_fields(master),
        include_field_codes=include_field_codes,
        explicit_rules=(payload or precursor).get("promotion_rules") or precursor.get("promotion_rules"),
    )


def _routing_payload(
    projection_id: str,
    routing: Mapping[str, Any],
    precursor: Mapping[str, Any],
    lexicon: Mapping[str, Any],
    domain_ids: list[str],
    section_roles: list[str],
    party_roles: list[str],
    example_types: list[str],
) -> dict[str, Any]:
    return {
        "when_to_use": str(routing.get("when_to_use") or precursor.get("description") or f"Use for {projection_id}."),
        "avoid_when": str(routing.get("avoid_when") or "Do not use when the samples have no relation to this custom projection."),
        "example_document_types": example_types,
        "section_roles": section_roles,
        "party_roles": party_roles,
        "surface_signals": {
            "text_markers": text_list(lexicon.get("text_markers")),
            "domain_markers": domain_markers(lexicon.get("domain_markers"), allowed_domains=domain_ids),
            "section_roles": section_roles,
            "party_roles": party_roles,
        },
    }


def domain_markers(value: Any, *, allowed_domains: list[str]) -> dict[str, list[str]]:
    allowed = {domain_id for domain_id in allowed_domains if domain_id}
    if isinstance(value, Mapping):
        return {str(key): text_list(markers) for key, markers in value.items() if str(key) in allowed and text_list(markers)}
    if not isinstance(value, list):
        return {}
    result: dict[str, list[str]] = {}
    for item in value:
        if isinstance(item, Mapping):
            domain_id = str(item.get("domain_id") or "")
            markers = text_list(item.get("markers"))
            if domain_id in allowed and markers:
                result[domain_id] = markers
    return result
