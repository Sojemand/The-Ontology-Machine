from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..models.serialization import utc_now_iso
from ..semantic_release.kernel_candidate import stable_hash
from ..taxonomy import SEMANTIC_RELEASE_SCHEMA_VERSION, upgrade_master_taxonomy_v2
from .control_language import control_locale_or_default
from .promotion_rules import clone_promotion_slots

DEFAULT_CUSTOM_RELEASE_VERSION = "custom.v1"
MASTER_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
    "promotion_slots",
    "entity_types",
    "role_types",
    "relation_types",
)


def base_release_payload(payload: Mapping[str, Any], *, release_ref: Mapping[str, Any]) -> dict[str, Any]:
    base_release_path = str(payload.get("base_release_path") or "").strip()
    if base_release_path:
        return read_release_payload(base_release_path)
    taxonomy_ref = mapping(release_ref, "taxonomy_ref") or mapping(payload, "taxonomy_ref")
    if not taxonomy_ref:
        raise ValueError("base_release_path or release_ref.taxonomy_ref is required.")
    master = master_taxonomy_from_ref(taxonomy_ref, release_ref=release_ref)
    master_id = require_text(master.get("taxonomy_id"), "release_ref.taxonomy_ref.taxonomy_id")
    master_version = require_text(master.get("taxonomy_version"), "release_ref.taxonomy_ref.taxonomy_version")
    taxonomy_release_id = str(taxonomy_ref.get("taxonomy_fingerprint") or stable_hash(repr(sorted(master.items()))))
    return {
        "schema_version": SEMANTIC_RELEASE_SCHEMA_VERSION,
        "release_id": str(release_ref.get("release_id") or "custom.semantic_release.base"),
        "release_version": str(release_ref.get("release_version") or DEFAULT_CUSTOM_RELEASE_VERSION),
        "master_taxonomy_id": master_id,
        "master_taxonomy_version": master_version,
        "master_taxonomy_release_id": taxonomy_release_id,
        "runtime_locale": control_locale_or_default(release_ref.get("runtime_locale"), taxonomy_ref.get("runtime_locale"), payload.get("runtime_locale")),
        "projection_ids": [],
        "materialization_version": "1",
        "created_at": utc_now_iso(),
        "fingerprint": stable_hash(repr(sorted(master.items()))),
        "master_taxonomy": master,
        "projections": [],
    }


def read_release_payload(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if path.is_dir():
        path = path / "release.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"base_release_path not found: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("base_release_path must point to a release JSON object.")
    return payload


def master_taxonomy_from_ref(taxonomy_ref: Mapping[str, Any], *, release_ref: Mapping[str, Any]) -> dict[str, Any]:
    master = mapping(taxonomy_ref, "master_taxonomy") or mapping(taxonomy_ref, "taxonomy_core")
    for key in MASTER_SECTIONS:
        if key not in master and isinstance(taxonomy_ref.get(key), list):
            master[key] = [dict(item) for item in taxonomy_ref[key] if isinstance(item, Mapping)]
    master["taxonomy_id"] = str(master.get("taxonomy_id") or taxonomy_ref.get("taxonomy_id") or "custom.taxonomy")
    master["taxonomy_version"] = str(master.get("taxonomy_version") or taxonomy_ref.get("taxonomy_version") or release_ref.get("release_version") or DEFAULT_CUSTOM_RELEASE_VERSION)
    master["schema_version"] = str(master.get("schema_version") or SEMANTIC_RELEASE_SCHEMA_VERSION)
    if "fallback_codes" not in master and isinstance(taxonomy_ref.get("fallback_code_map"), Mapping):
        master["fallback_codes"] = dict(taxonomy_ref["fallback_code_map"])
    if "promotion_slots" not in master:
        master["promotion_slots"] = clone_promotion_slots(taxonomy_ref.get("promotion_slots"))
    apply_taxonomy_terms(master, taxonomy_ref)
    upgraded = upgrade_master_taxonomy_v2(master, include_semantic_defaults=False)
    derive_custom_semantic_sections(upgraded)
    return upgraded


def derive_custom_semantic_sections(master: dict[str, Any]) -> None:
    if "entity_types" not in master:
        master["entity_types"] = [
            {"code": code, "label": label_from_code(code)}
            for code in semantic_binding_codes(master, "entity_type")
        ]
    if "role_types" not in master:
        master["role_types"] = [
            {"code": code, "label": label_from_code(code)}
            for code in semantic_binding_codes(master, "role_type")
        ]


def semantic_binding_codes(master: Mapping[str, Any], binding_key: str) -> list[str]:
    seen: set[str] = set()
    codes: list[str] = []
    for section in ("field_codes", "row_types"):
        for item in master.get(section, []) or []:
            if not isinstance(item, Mapping):
                continue
            binding = item.get("semantic_binding")
            if not isinstance(binding, Mapping):
                continue
            code = str(binding.get(binding_key) or "").strip()
            if code and code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


def apply_taxonomy_terms(master: dict[str, Any], taxonomy_ref: Mapping[str, Any]) -> None:
    terms = mapping(mapping(taxonomy_ref, "taxonomy_text"), "terms")
    for section in MASTER_SECTIONS:
        term_by_code = {
            str(item.get("code") or "").strip(): item
            for item in terms.get(section, [])
            if isinstance(item, Mapping) and str(item.get("code") or "").strip()
        }
        enriched = [enrich_taxonomy_item(item, term_by_code) for item in master.get(section, []) or [] if isinstance(item, Mapping)]
        if enriched:
            master[section] = enriched


def enrich_taxonomy_item(item: Mapping[str, Any], term_by_code: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    current = dict(item)
    term = term_by_code.get(str(current.get("code") or current.get("id") or "").strip(), {})
    if term.get("label") and not current.get("label"):
        current["label"] = term["label"]
    if term.get("description") and not current.get("description"):
        current["description"] = term["description"]
    if "aliases" not in current and isinstance(term.get("aliases"), list):
        current["aliases"] = list(term["aliases"])
    return current


def master_fields(master: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = master.get("field_codes")
    if not isinstance(fields, list):
        return []
    return [dict(item) for item in fields if isinstance(item, Mapping)]


def taxonomy_fallback_domains(base_release: Mapping[str, Any]) -> list[str]:
    domains = mapping(base_release, "master_taxonomy").get("domains")
    if isinstance(domains, list):
        ids = [str(item.get("id") or item.get("code") or "").strip() for item in domains if isinstance(item, Mapping)]
        return ["other"] if "other" in ids else ([ids[0]] if ids else ["other"])
    return ["other"]


def mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(text for item in value if (text := str(item or "").strip())))


def canonical_texts(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()}, key=lambda item: (item.casefold(), item))


def label_from_code(code: str) -> str:
    return " ".join(part.capitalize() for part in str(code).split("_") if part) or "Other"


def require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required.")
    return text
