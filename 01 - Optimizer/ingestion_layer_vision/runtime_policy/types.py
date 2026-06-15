"""Typed carriers for runtime OCR policy bundles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION = "runtime_semantic_assets_v1"
VISION_POLICY_BUNDLE_VERSION = "vision_policy_bundle_v1"


@dataclass(frozen=True, slots=True)
class RuntimeOcrPolicy:
    policy_version: str
    source_mode: str
    defaults: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VisionPolicyBundle:
    bundle_version: str
    release_fingerprint: str
    ocr_policy: RuntimeOcrPolicy


@dataclass(frozen=True, slots=True)
class RuntimeSemanticAssetsRecord:
    schema_version: str
    release_id: str
    release_version: str
    release_fingerprint: str
    master_taxonomy_id: str
    master_taxonomy_version: str
    projection_catalog: dict[str, Any]
    vision_policy_bundle: VisionPolicyBundle


@dataclass(frozen=True, slots=True)
class RuntimePolicyState:
    release_id: str
    release_version: str
    release_fingerprint: str
    bundle_version: str
    ocr_policy: RuntimeOcrPolicy
