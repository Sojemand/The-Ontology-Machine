from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .kernel_candidate import stable_hash
from .kernel_merge_common import merged_text_list
from .kernel_merge_projection_text import (
    merged_avoid_when,
    merged_projection_description,
    merged_projection_label,
    merged_when_to_use,
)


def merge_projection_refs_to_single(
    refs: Sequence[Mapping[str, Any]],
    *,
    taxonomy_ref: Mapping[str, Any],
    merge_run_id: str,
) -> list[dict[str, Any]]:
    if not refs:
        return []
    seed = stable_hash(repr([dict(item) for item in refs]))
    projection_id = f"merged.projection.{seed[:12]}"
    projection_fingerprint = stable_hash(f"projection:{merge_run_id}:{seed}")
    payload = _merged_projection_payload(
        refs,
        taxonomy_ref=taxonomy_ref,
        projection_id=projection_id,
        projection_fingerprint=projection_fingerprint,
    )
    return [
        {
            "included_taxonomy_codes": _included_taxonomy_codes(payload),
            "projection_fingerprint": projection_fingerprint,
            "projection_id": projection_id,
            "projection_payload": payload,
        }
    ]


def _merged_projection_payload(
    refs: Sequence[Mapping[str, Any]],
    *,
    taxonomy_ref: Mapping[str, Any],
    projection_id: str,
    projection_fingerprint: str,
) -> dict[str, Any]:
    source_payloads = [
        dict(item.get("projection_payload") or {})
        for item in refs
        if isinstance(item.get("projection_payload"), Mapping)
    ]
    source_ids = merged_text_list(refs, "projection_id")
    master = dict(taxonomy_ref.get("master_taxonomy") or taxonomy_ref.get("taxonomy_core") or {})
    payload = {
        "projection_id": projection_id,
        "master_taxonomy_id": str(taxonomy_ref.get("taxonomy_id") or master.get("taxonomy_id") or ""),
        "master_taxonomy_version": str(taxonomy_ref.get("taxonomy_version") or master.get("taxonomy_version") or ""),
        "domain_ids": _projection_codes(source_payloads, refs, master, "domain_ids", "domains"),
        "projection_family": "custom",
        "projection_version": "merged.v1",
        "projection_fingerprint": projection_fingerprint,
        "extends": [],
        "materialization_profile_id": "document_entities.v1",
        "compatibility": {"source_projection_ids": source_ids},
        "include_document_types": _projection_codes(source_payloads, refs, master, "include_document_types", "document_types"),
        "include_categories": _projection_codes(source_payloads, refs, master, "include_categories", "categories"),
        "include_subcategories": _projection_codes(source_payloads, refs, master, "include_subcategories", "subcategories"),
        "include_field_codes": _projection_codes(source_payloads, refs, master, "include_field_codes", "field_codes"),
        "include_row_types": _projection_codes(source_payloads, refs, master, "include_row_types", "row_types"),
        "include_cell_codes": _projection_codes(source_payloads, refs, master, "include_cell_codes", "cell_codes"),
    }
    payload["label"] = merged_projection_label(source_payloads, master, payload)
    payload["description"] = merged_projection_description(source_payloads, master, payload)
    payload["routing"] = _merged_routing(source_payloads, master=master, payload=payload)
    rules = _merged_promotion_rules(source_payloads)
    if rules:
        payload["promotion_rules"] = rules
    return payload


def _projection_codes(
    source_payloads: Sequence[Mapping[str, Any]],
    refs: Sequence[Mapping[str, Any]],
    master: Mapping[str, Any],
    payload_key: str,
    taxonomy_section: str,
) -> list[str]:
    values: set[str] = set()
    for payload in source_payloads:
        raw = payload.get(payload_key)
        if isinstance(raw, list):
            values.update(str(item).strip() for item in raw if str(item).strip())
    section_codes = _section_codes(master, taxonomy_section)
    if not values:
        included = merged_text_list(refs, "included_taxonomy_codes")
        values.update(code for code in included if code in section_codes)
    if not values:
        values.update(section_codes)
    return sorted(values)


def _section_codes(master: Mapping[str, Any], section: str) -> set[str]:
    values = master.get(section)
    if not isinstance(values, list):
        return set()
    return {
        str(item.get("code") or item.get("id") or "").strip()
        for item in values
        if isinstance(item, Mapping) and str(item.get("code") or item.get("id") or "").strip()
    }


def _merged_routing(
    source_payloads: Sequence[Mapping[str, Any]],
    *,
    master: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    example_types: set[str] = set()
    section_roles: set[str] = set()
    party_roles: set[str] = set()
    text_markers: set[str] = set()
    domain_markers: dict[str, set[str]] = {}
    for payload in source_payloads:
        routing = payload.get("routing")
        if not isinstance(routing, Mapping):
            continue
        example_types.update(_texts(routing.get("example_document_types")))
        section_roles.update(_texts(routing.get("section_roles")))
        party_roles.update(_texts(routing.get("party_roles")))
        signals = routing.get("surface_signals")
        if not isinstance(signals, Mapping):
            continue
        text_markers.update(_texts(signals.get("text_markers")))
        section_roles.update(_texts(signals.get("section_roles")))
        party_roles.update(_texts(signals.get("party_roles")))
        markers = signals.get("domain_markers")
        if isinstance(markers, Mapping):
            for domain_id, values in markers.items():
                bucket = domain_markers.setdefault(str(domain_id), set())
                bucket.update(_texts(values))
    routing = {
        "example_document_types": sorted(example_types) or ["other"],
        "section_roles": sorted(section_roles) or ["body", "other"],
        "party_roles": sorted(party_roles) or ["other"],
        "surface_signals": {
            "text_markers": sorted(text_markers),
            "domain_markers": {key: sorted(values) for key, values in sorted(domain_markers.items())},
            "section_roles": sorted(section_roles) or ["body", "other"],
            "party_roles": sorted(party_roles) or ["other"],
        },
    }
    routing["when_to_use"] = merged_when_to_use(source_payloads, master, payload, routing)
    routing["avoid_when"] = merged_avoid_when(source_payloads, master, payload, routing)
    return routing


def _merged_promotion_rules(source_payloads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rules_by_slot: dict[str, dict[str, Any]] = {}
    for payload in source_payloads:
        raw = payload.get("promotion_rules")
        if not isinstance(raw, list):
            continue
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            slot = str(item.get("slot") or "").strip()
            if not slot:
                continue
            source_paths = _promotion_source_paths(item)
            if not source_paths:
                continue
            rule = rules_by_slot.get(slot)
            if rule is None:
                rule = {
                    key: deepcopy(value)
                    for key, value in item.items()
                    if key not in {"source_field", "source_paths"}
                }
                rule["slot"] = slot
                rule["source_paths"] = []
                rules_by_slot[slot] = rule
            rule["source_paths"] = _dedupe_texts([*rule["source_paths"], *source_paths])
    return list(rules_by_slot.values())


def _promotion_source_paths(rule: Mapping[str, Any]) -> list[str]:
    source_paths = rule.get("source_paths")
    if isinstance(source_paths, list):
        return _dedupe_texts(source_paths)
    source_field = str(rule.get("source_field") or "").strip()
    if source_field:
        return [f"content.fields.{source_field}"]
    return []


def _dedupe_texts(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _included_taxonomy_codes(payload: Mapping[str, Any]) -> list[str]:
    codes: set[str] = set()
    for key in (
        "domain_ids",
        "include_document_types",
        "include_categories",
        "include_subcategories",
        "include_field_codes",
        "include_row_types",
        "include_cell_codes",
    ):
        codes.update(_texts(payload.get(key)))
    return sorted(codes)


def _texts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
