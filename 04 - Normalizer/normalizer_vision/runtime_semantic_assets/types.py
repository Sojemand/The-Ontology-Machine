"""Named contracts for runtime semantic assets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION = "runtime_semantic_assets_v1"
VISION_POLICY_BUNDLE_VERSION = "vision_policy_bundle_v1"


@dataclass(frozen=True, slots=True)
class RuntimeProjectionCatalogEntry:
    projection_id: str
    label: str
    when_to_use: str
    avoid_when: str
    example_document_types: list[str]
    promotion_rules: list[dict[str, Any]]
    field_slot_map: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "label": self.label,
            "when_to_use": self.when_to_use,
            "avoid_when": self.avoid_when,
            "example_document_types": list(self.example_document_types),
            "promotion_rules": [dict(item) for item in self.promotion_rules],
            "field_slot_map": dict(self.field_slot_map),
        }


@dataclass(frozen=True, slots=True)
class RuntimeProjectionCatalog:
    catalog_version: str
    release_id: str
    release_version: str
    release_fingerprint: str
    master_taxonomy_id: str
    master_taxonomy_version: str
    projections: list[RuntimeProjectionCatalogEntry]
    master_taxonomy_release_id: str | None = None
    runtime_locale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "catalog_version": self.catalog_version,
            "release_id": self.release_id,
            "release_version": self.release_version,
            "release_fingerprint": self.release_fingerprint,
            "master_taxonomy_id": self.master_taxonomy_id,
            "master_taxonomy_version": self.master_taxonomy_version,
            "projections": [entry.to_dict() for entry in self.projections],
        }
        if self.master_taxonomy_release_id:
            payload["master_taxonomy_release_id"] = self.master_taxonomy_release_id
        if self.runtime_locale:
            payload["runtime_locale"] = self.runtime_locale
        return payload


@dataclass(frozen=True, slots=True)
class RuntimeSemanticPolicy:
    policy_version: str
    source_mode: str
    defaults: dict[str, Any]
    projection_overrides: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "policy_version": self.policy_version,
            "source_mode": self.source_mode,
            "defaults": dict(self.defaults),
        }
        if self.projection_overrides is not None:
            payload["projection_overrides"] = dict(self.projection_overrides)
        return payload


@dataclass(frozen=True, slots=True)
class VisionPolicyBundle:
    bundle_version: str
    release_fingerprint: str
    ocr_policy: RuntimeSemanticPolicy
    semantic_extraction_policy: RuntimeSemanticPolicy

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "release_fingerprint": self.release_fingerprint,
            "ocr_policy": self.ocr_policy.to_dict(),
            "semantic_extraction_policy": self.semantic_extraction_policy.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RuntimeSemanticAssets:
    schema_version: str
    release_id: str
    release_version: str
    release_fingerprint: str
    master_taxonomy_id: str
    master_taxonomy_version: str
    promotion_slots: list[dict[str, Any]]
    projection_catalog: RuntimeProjectionCatalog
    vision_policy_bundle: VisionPolicyBundle
    master_taxonomy_release_id: str | None = None
    runtime_locale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "release_id": self.release_id,
            "release_version": self.release_version,
            "release_fingerprint": self.release_fingerprint,
            "master_taxonomy_id": self.master_taxonomy_id,
            "master_taxonomy_version": self.master_taxonomy_version,
            "promotion_slots": [dict(item) for item in self.promotion_slots],
            "projection_catalog": self.projection_catalog.to_dict(),
            "vision_policy_bundle": self.vision_policy_bundle.to_dict(),
        }
        if self.master_taxonomy_release_id:
            payload["master_taxonomy_release_id"] = self.master_taxonomy_release_id
        if self.runtime_locale:
            payload["runtime_locale"] = self.runtime_locale
        return payload
