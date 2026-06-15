"""Pure compilation helpers for runtime semantic assets."""
from __future__ import annotations

from typing import Any

from ..taxonomy_sources import policy as source_policy
from ..shared_identity import build_projection_catalog_version
from .semantic_policy import build_semantic_extraction_policy
from .types import (
    RuntimeProjectionCatalog,
    RuntimeProjectionCatalogEntry,
    RuntimeSemanticPolicy,
    VISION_POLICY_BUNDLE_VERSION,
    VisionPolicyBundle,
)

_OCR_POLICY_VERSION = "ocr_policy_v1"
_LAYOUT_PROFILE_ID = "layout_fidelity_v1"
_BALANCED_PROFILE_ID = "balanced_text_v1"
_LAYOUT_DOMAINS = frozenset({"finance", "property", "technical", "health"})
_LLM_OCR_PLUGIN = "optimizer-llm-ocr"


def build_projection_catalog(release: dict[str, Any]) -> RuntimeProjectionCatalog:
    projections = [item for item in release.get("projections", []) or [] if isinstance(item, dict)]
    master = release.get("master_taxonomy") if isinstance(release.get("master_taxonomy"), dict) else {}
    projections_by_id = {
        str(item.get("projection_id") or "").strip(): item
        for item in projections
        if str(item.get("projection_id") or "").strip()
    }
    ordered_ids = source_policy.canonical_projection_id_list(
        list(projections_by_id),
        label="release.projections",
    )
    entries = [_build_projection_catalog_entry(projections_by_id[projection_id], master=master) for projection_id in ordered_ids]
    catalog = RuntimeProjectionCatalog(
        catalog_version="",
        release_id=str(release.get("release_id") or ""),
        release_version=str(release.get("release_version") or ""),
        release_fingerprint=str(release.get("fingerprint") or ""),
        master_taxonomy_id=str(release.get("master_taxonomy_id") or ""),
        master_taxonomy_version=str(release.get("master_taxonomy_version") or ""),
        master_taxonomy_release_id=str(release.get("master_taxonomy_release_id") or "").strip() or None,
        runtime_locale=str(release.get("runtime_locale") or "").strip() or None,
        projections=entries,
    )
    return RuntimeProjectionCatalog(
        catalog_version=build_catalog_version(catalog),
        release_id=catalog.release_id,
        release_version=catalog.release_version,
        release_fingerprint=catalog.release_fingerprint,
        master_taxonomy_id=catalog.master_taxonomy_id,
        master_taxonomy_version=catalog.master_taxonomy_version,
        master_taxonomy_release_id=catalog.master_taxonomy_release_id,
        runtime_locale=catalog.runtime_locale,
        projections=catalog.projections,
    )


def build_catalog_version(catalog: RuntimeProjectionCatalog | dict[str, Any]) -> str:
    payload = catalog.to_dict() if isinstance(catalog, RuntimeProjectionCatalog) else dict(catalog)
    return build_projection_catalog_version(payload)


def build_vision_policy_bundle(release: dict[str, Any], *, release_fingerprint: str) -> VisionPolicyBundle:
    return VisionPolicyBundle(
        bundle_version=VISION_POLICY_BUNDLE_VERSION,
        release_fingerprint=release_fingerprint,
        ocr_policy=_build_ocr_policy(release),
        semantic_extraction_policy=build_semantic_extraction_policy(release),
    )


def _build_projection_catalog_entry(payload: dict[str, Any], *, master: dict[str, Any]) -> RuntimeProjectionCatalogEntry:
    routing = payload.get("routing") or {}
    return RuntimeProjectionCatalogEntry(
        projection_id=str(payload.get("projection_id") or "").strip(),
        label=str(payload.get("label") or "").strip(),
        when_to_use=str(routing.get("when_to_use") or "").strip(),
        avoid_when=str(routing.get("avoid_when") or "").strip(),
        example_document_types=[str(item).strip() for item in routing.get("example_document_types", []) if str(item).strip()],
        promotion_rules=_promotion_rules(payload.get("promotion_rules")),
        field_slot_map=_field_slot_map(master, payload),
    )


def _build_ocr_policy(release: dict[str, Any]) -> RuntimeSemanticPolicy:
    profile_id = _LAYOUT_PROFILE_ID if _layout_profile_selected(release) else _BALANCED_PROFILE_ID
    return RuntimeSemanticPolicy(
        policy_version=_OCR_POLICY_VERSION,
        source_mode="release_domain_merge",
        defaults=_ocr_defaults(profile_id),
    )

def _layout_profile_selected(release: dict[str, Any]) -> bool:
    tokens = {_normalize_token(token) for token in _iter_release_policy_tokens(release)}
    return any(token in _LAYOUT_DOMAINS for token in tokens)


def _iter_release_policy_tokens(release: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for projection in release.get("projections", []) or []:
        if not isinstance(projection, dict):
            continue
        tokens.extend(_projection_tokens(projection))
    return tokens


def _projection_tokens(projection: dict[str, Any]) -> list[str]:
    domain_ids = _normalized_text_list(projection.get("domain_ids"))
    if domain_ids:
        return domain_ids
    include_categories = _normalized_text_list(projection.get("include_categories"))
    if include_categories:
        return include_categories
    prefix = _normalize_token(str(projection.get("projection_id") or "").split(".", 1)[0])
    return [prefix] if prefix else []


def _ocr_defaults(profile_id: str) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "scan": {"min_chars_per_page": 80 if profile_id == _LAYOUT_PROFILE_ID else 50, "use_has_images": True},
        "vision_route": {"images_always_vision": True, "pdf_scans_use_vision": True},
        "ocr_plugin": {"preferred_plugin": _LLM_OCR_PLUGIN, "force_backup_on_scan": True},
        "render": {
            "page_image_dpi": 150,
            "page_image_quality": 95,
            "serializer_quality_mode": "best_quality" if profile_id == _LAYOUT_PROFILE_ID else "balanced",
            "ocr_render_dpi": 450 if profile_id == _LAYOUT_PROFILE_ID else 300,
        },
    }


def _normalized_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (_normalize_token(entry) for entry in value) if item]


def _promotion_rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict) and item.get("slot")]


def _field_slot_map(master: dict[str, Any], projection: dict[str, Any]) -> dict[str, str]:
    included = {str(code) for code in projection.get("include_field_codes", []) if str(code)}
    result: dict[str, str] = {}
    fields = master.get("field_codes")
    if not isinstance(fields, list):
        return result
    for field in fields:
        if not isinstance(field, dict):
            continue
        code = str(field.get("code") or "").strip()
        slot = str(field.get("promotion_slot") or "").strip()
        if code and slot and code in included:
            result[code] = slot
    return result


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", ".").replace(" ", ".")
