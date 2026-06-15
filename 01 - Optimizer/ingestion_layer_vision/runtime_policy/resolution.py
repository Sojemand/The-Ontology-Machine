"""Resolution helpers that turn runtime assets into OCR processor state."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .ocr_policy import normalize_page_image_render_defaults
from .repository import load_runtime_semantic_assets
from .types import RuntimeOcrPolicy, RuntimePolicyState, RuntimeSemanticAssetsRecord, VisionPolicyBundle
from .validation import validate_runtime_semantic_assets


def load_runtime_policy_state(path: Path) -> RuntimePolicyState:
    return resolve_runtime_policy_state(load_runtime_semantic_assets(path))


def resolve_runtime_policy_state(payload: dict[str, Any]) -> RuntimePolicyState:
    record = parse_runtime_semantic_assets(payload)
    bundle = record.vision_policy_bundle
    return RuntimePolicyState(
        release_id=record.release_id,
        release_version=record.release_version,
        release_fingerprint=record.release_fingerprint,
        bundle_version=bundle.bundle_version,
        ocr_policy=bundle.ocr_policy,
    )


def parse_runtime_semantic_assets(payload: dict[str, Any]) -> RuntimeSemanticAssetsRecord:
    assets = validate_runtime_semantic_assets(payload)
    return RuntimeSemanticAssetsRecord(
        schema_version=str(assets.get("schema_version") or ""),
        release_id=str(assets.get("release_id") or ""),
        release_version=str(assets.get("release_version") or ""),
        release_fingerprint=str(assets.get("release_fingerprint") or ""),
        master_taxonomy_id=str(assets.get("master_taxonomy_id") or ""),
        master_taxonomy_version=str(assets.get("master_taxonomy_version") or ""),
        projection_catalog=dict(assets.get("projection_catalog") or {}),
        vision_policy_bundle=_bundle_from_dict(assets.get("vision_policy_bundle") or {}),
    )


def _bundle_from_dict(payload: dict[str, Any]) -> VisionPolicyBundle:
    return VisionPolicyBundle(
        bundle_version=str(payload.get("bundle_version") or ""),
        release_fingerprint=str(payload.get("release_fingerprint") or ""),
        ocr_policy=_policy_from_dict(payload.get("ocr_policy") or {}),
    )


def _policy_from_dict(payload: dict[str, Any]) -> RuntimeOcrPolicy:
    return RuntimeOcrPolicy(
        policy_version=str(payload.get("policy_version") or ""),
        source_mode=str(payload.get("source_mode") or ""),
        defaults=normalize_page_image_render_defaults(dict(payload.get("defaults") or {})),
    )
