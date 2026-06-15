from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


MODULE_ROOT = Path(__file__).resolve().parents[2]
LLM_FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"
DEFAULT_RELEASE_FIXTURE = MODULE_ROOT / "dev-tests" / "fixtures" / "phase9" / "default_semantic_release" / "release.json"


def load_llm_fixtures() -> dict[str, Any]:
    return json.loads(LLM_FIXTURES.read_text(encoding="utf-8"))


def load_default_release_fixture() -> dict[str, Any]:
    return json.loads(DEFAULT_RELEASE_FIXTURE.read_text(encoding="utf-8"))


def codes_from_taxonomy_core(taxonomy_core: Mapping[str, Any]) -> list[str]:
    codes = {"other"}
    for values in taxonomy_core.values():
        if isinstance(values, list):
            for item in values:
                if isinstance(item, Mapping) and isinstance(item.get("code"), str):
                    codes.add(item["code"])
    return sorted(codes)


def included_projection_codes(precursor: Mapping[str, Any]) -> list[str]:
    codes: list[str] = []
    for key in (
        "domain_ids",
        "include_document_types",
        "include_categories",
        "include_subcategories",
        "include_field_codes",
        "include_row_types",
        "include_cell_codes",
    ):
        value = precursor.get(key)
        if isinstance(value, list):
            codes.extend(str(item) for item in value if str(item))
    return list(dict.fromkeys(codes))


def projection_refs_from_component_identity(component_identity: Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(component_identity.get("projection_refs"), list):
        return [dict(item) for item in component_identity["projection_refs"] if isinstance(item, Mapping)]
    if component_identity.get("projection_id") or component_identity.get("projection_ids"):
        return [dict(component_identity)]
    return []
