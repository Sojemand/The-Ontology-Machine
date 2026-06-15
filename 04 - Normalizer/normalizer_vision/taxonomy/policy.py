"""Pure taxonomy upgrade, merge, and fingerprint policy."""
from __future__ import annotations

import copy
import json
from typing import Any

from ..models.serialization import sha256_bytes
from .binding_defaults import default_cell_binding, default_field_binding, default_row_binding
from .promotion_rules import validate_promotion_rules
from .semantic_defaults import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_MASTER_COMPATIBILITY,
    DEFAULT_RELATION_TYPES,
    DEFAULT_ROLE_TYPES,
)
from .types import (
    DEFAULT_MATERIALIZATION_PROFILE_ID,
    DEFAULT_PROJECTION_FAMILY,
    DEFAULT_PROJECTION_VERSION,
    JsonDict,
    PROJECTION_SECTION_SPECS,
    SEMANTIC_RELEASE_SCHEMA_VERSION,
)
from .surface_signals import normalize_surface_signals
from .validation import ensure_master_required_keys, validate_projection_includes


def deepcopy_json(value: Any) -> Any:
    return copy.deepcopy(value)


def dedupe_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def profile_fingerprint(payload: JsonDict) -> str:
    fingerprint_payload = deepcopy_json(payload)
    fingerprint_payload.pop("projection_fingerprint", None)
    canonical = json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def merge_semantic_binding(default_binding: JsonDict, explicit_binding: Any) -> JsonDict:
    binding = deepcopy_json(default_binding)
    if isinstance(explicit_binding, dict):
        binding.update({str(key): value for key, value in explicit_binding.items()})
    return binding


def _neutral_field_binding(code: str) -> JsonDict:
    return {"entity_type": "document_fact", "attribute_code": code or "other"}


def _neutral_row_binding(code: str) -> JsonDict:
    return {"entity_type": "document_fact", "role_type": code or "other", "materialize_each_row": False}


def _neutral_cell_binding(code: str) -> JsonDict:
    return {"attribute_code": code or "other", "materialize_on_row_entity": True}


def upgrade_master_taxonomy_v2(data: JsonDict, *, include_semantic_defaults: bool = True) -> JsonDict:
    upgraded = deepcopy_json(data)
    upgraded["schema_version"] = str(upgraded.get("schema_version") or SEMANTIC_RELEASE_SCHEMA_VERSION)
    if include_semantic_defaults:
        upgraded.setdefault("entity_types", deepcopy_json(DEFAULT_ENTITY_TYPES))
        upgraded.setdefault("role_types", deepcopy_json(DEFAULT_ROLE_TYPES))
        upgraded.setdefault("relation_types", deepcopy_json(DEFAULT_RELATION_TYPES))
        upgraded.setdefault("compatibility", deepcopy_json(DEFAULT_MASTER_COMPATIBILITY))
    upgraded.setdefault("promotion_slots", [])
    field_binding = default_field_binding if include_semantic_defaults else _neutral_field_binding
    row_binding = default_row_binding if include_semantic_defaults else _neutral_row_binding
    cell_binding = default_cell_binding if include_semantic_defaults else _neutral_cell_binding
    for item in upgraded.get("field_codes", []) or []:
        if isinstance(item, dict):
            code = str(item.get("code", "")).strip()
            item["semantic_binding"] = merge_semantic_binding(field_binding(code), item.get("semantic_binding"))
    for item in upgraded.get("row_types", []) or []:
        if isinstance(item, dict):
            code = str(item.get("code", "")).strip()
            item["semantic_binding"] = merge_semantic_binding(row_binding(code), item.get("semantic_binding"))
    for item in upgraded.get("cell_codes", []) or []:
        if isinstance(item, dict):
            code = str(item.get("code", "")).strip()
            item["semantic_binding"] = merge_semantic_binding(cell_binding(code), item.get("semantic_binding"))
    templates = [upgrade_projection_payload_v2(upgraded, template) for template in upgraded.get("projection_templates", []) or [] if isinstance(template, dict)]
    if templates:
        upgraded["projection_templates"] = templates
    return upgraded


def upgrade_projection_payload_v2(master: JsonDict, payload: JsonDict) -> JsonDict:
    master_for_projection = deepcopy_json(master)
    master_for_projection["projection_templates"] = []
    validated_master = ensure_master_required_keys(upgrade_master_taxonomy_v2(master_for_projection))
    projection_id = str(payload.get("projection_id") or payload.get("id") or "").strip()
    label = str(payload.get("label", "")).strip()
    if not projection_id:
        raise ValueError("projection_id darf nicht leer sein.")
    if not label:
        raise ValueError("label darf nicht leer sein.")
    data: JsonDict = {
        "schema_version": str(payload.get("schema_version", SEMANTIC_RELEASE_SCHEMA_VERSION)),
        "projection_id": projection_id,
        "label": label,
        "description": str(payload.get("description", "")).strip(),
        "master_taxonomy_id": str(payload.get("master_taxonomy_id") or validated_master.get("taxonomy_id", "normalizer_taxonomy.master")),
        "master_taxonomy_version": str(payload.get("master_taxonomy_version") or validated_master.get("taxonomy_version", "")),
        "domain_ids": dedupe_strings(list(payload.get("domain_ids", []))),
        "projection_family": str(payload.get("projection_family", "")).strip() or DEFAULT_PROJECTION_FAMILY,
        "projection_version": str(payload.get("projection_version", "")).strip() or DEFAULT_PROJECTION_VERSION,
        "extends": dedupe_strings(list(payload.get("extends", []))),
        "materialization_profile_id": str(payload.get("materialization_profile_id", "")).strip() or DEFAULT_MATERIALIZATION_PROFILE_ID,
        "compatibility": deepcopy_json(payload.get("compatibility", {})) if isinstance(payload.get("compatibility"), dict) else {},
        "promotion_rules": deepcopy_json(payload.get("promotion_rules", [])) if isinstance(payload.get("promotion_rules"), list) else [],
    }
    if isinstance(payload.get("routing"), dict):
        data["routing"] = deepcopy_json(payload["routing"])
        if "surface_signals" in data["routing"]:
            data["routing"]["surface_signals"] = normalize_surface_signals(
                data["routing"]["surface_signals"],
                projection_id=projection_id,
                domain_ids=data["domain_ids"],
            )
    for _, include_key, _ in PROJECTION_SECTION_SPECS:
        data[include_key] = dedupe_strings(list(payload.get(include_key, [])))
    validate_projection_includes(validated_master, data)
    validate_promotion_rules(
        validated_master,
        data,
        strict_source_paths=data["projection_family"] == "custom",
    )
    data["projection_fingerprint"] = profile_fingerprint(data)
    return data
