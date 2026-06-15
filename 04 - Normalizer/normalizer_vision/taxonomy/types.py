"""Named taxonomy carriers and stable constants."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, TypeAlias

JsonDict: TypeAlias = dict[str, Any]
SectionSpec: TypeAlias = tuple[str, str, str]

MASTER_REQUIRED_KEYS = [
    "taxonomy_id",
    "taxonomy_version",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
]
PROJECTION_SECTION_SPECS: tuple[SectionSpec, ...] = (
    ("document_types", "include_document_types", "code"),
    ("categories", "include_categories", "code"),
    ("subcategories", "include_subcategories", "code"),
    ("field_codes", "include_field_codes", "code"),
    ("row_types", "include_row_types", "code"),
    ("cell_codes", "include_cell_codes", "code"),
)
PROJECTION_REQUIRED_KEYS = [
    "projection_id",
    "label",
    *[include_key for _, include_key, _ in PROJECTION_SECTION_SPECS],
]

SEMANTIC_RELEASE_SCHEMA_VERSION = "1.0"
DEFAULT_PROJECTION_VERSION = "v2"
DEFAULT_PROJECTION_FAMILY = "default"
DEFAULT_MATERIALIZATION_PROFILE_ID = "document_entities.v1"

_SNAKE_CASE_RE = re.compile(r"[^a-z0-9]+")


def normalize_lookup_token(value: str) -> str:
    text = _SNAKE_CASE_RE.sub("_", value.strip().lower()).strip("_")
    return text or "other"


@dataclass
class TaxonomyProfile:
    projection_id: str
    label: str
    description: str
    master_taxonomy_id: str
    master_taxonomy_version: str
    domain_ids: list[str]
    projection_family: str
    projection_version: str
    materialization_profile_id: str
    promotion_rules: list[JsonDict]
    promotion_slots: list[JsonDict]
    compatibility: JsonDict
    projection_fingerprint: str
    surface_signals: JsonDict
    document_types: dict[str, JsonDict]
    categories: dict[str, JsonDict]
    subcategories: dict[str, JsonDict]
    field_codes: dict[str, JsonDict]
    row_types: dict[str, JsonDict]
    cell_codes: dict[str, JsonDict]
    _alias_maps: dict[str, dict[str, str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._alias_maps = {
            "document_type": self._build_alias_map(self.document_types),
            "category": self._build_alias_map(self.categories),
            "subcategory": self._build_alias_map(self.subcategories),
            "field": self._build_alias_map(self.field_codes),
            "row": self._build_alias_map(self.row_types),
            "cell": self._build_alias_map(self.cell_codes),
        }

    @staticmethod
    def _build_alias_map(items: dict[str, JsonDict]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for code, item in items.items():
            mapping[normalize_lookup_token(code)] = code
            mapping[normalize_lookup_token(str(item.get("label", code)))] = code
            for alias in item.get("aliases", []) or []:
                mapping[normalize_lookup_token(str(alias))] = code
        return mapping

    def canonical_code(self, kind: str, value: Any, fallback: str | None = "other") -> str | None:
        if value is None:
            return fallback
        raw = str(value).strip()
        if not raw:
            return fallback
        return self._alias_maps[kind].get(normalize_lookup_token(raw), fallback)

    def projection_metadata(self) -> JsonDict:
        return {
            "projection_id": self.projection_id,
            "projection_family": self.projection_family,
            "master_taxonomy_id": self.master_taxonomy_id,
            "master_taxonomy_version": self.master_taxonomy_version,
            "projection_version": self.projection_version,
            "projection_fingerprint": self.projection_fingerprint,
            "materialization_profile_id": self.materialization_profile_id,
        }


def profile_to_json(profile: TaxonomyProfile) -> str:
    payload = {
        "projection_id": profile.projection_id,
        "projection_family": profile.projection_family,
        "projection_version": profile.projection_version,
        "projection_fingerprint": profile.projection_fingerprint,
        "materialization_profile_id": profile.materialization_profile_id,
        "label": profile.label,
        "description": profile.description,
        "master_taxonomy_id": profile.master_taxonomy_id,
        "master_taxonomy_version": profile.master_taxonomy_version,
        "domain_ids": profile.domain_ids,
        "promotion_rules": profile.promotion_rules,
        "promotion_slots": profile.promotion_slots,
        "document_types": list(profile.document_types.values()),
        "categories": list(profile.categories.values()),
        "subcategories": list(profile.subcategories.values()),
        "field_codes": list(profile.field_codes.values()),
        "row_types": list(profile.row_types.values()),
        "cell_codes": list(profile.cell_codes.values()),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
