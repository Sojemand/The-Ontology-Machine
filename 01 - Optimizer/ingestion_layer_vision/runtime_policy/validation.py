"""Strict validation for runtime assets consumed by the vision processor."""
from __future__ import annotations

from typing import Any

from .types import RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION, VISION_POLICY_BUNDLE_VERSION

_RUNTIME_KEYS = frozenset({"schema_version", "release_id", "release_version", "release_fingerprint", "master_taxonomy_id", "master_taxonomy_version", "projection_catalog", "vision_policy_bundle"})
_PROJECTION_CATALOG_KEYS = frozenset({"catalog_version", "release_id", "release_version", "release_fingerprint", "master_taxonomy_id", "master_taxonomy_version", "projections"})
_POLICY_KEYS = frozenset({"policy_version", "source_mode", "defaults"})
_OCR_PROFILE_IDS = frozenset({"layout_fidelity_v1", "balanced_text_v1"})
_LLM_OCR_PLUGIN = "optimizer-llm-ocr"
_LEGACY_LOCAL_OCR_KEYS = frozenset({"device_policy", "paddlevl"})


def validate_runtime_semantic_assets(payload: Any) -> dict[str, Any]:
    assets = _require_dict(payload, "runtime_semantic_assets")
    missing = sorted(_RUNTIME_KEYS - set(assets))
    if missing:
        raise ValueError(f"runtime_semantic_assets unvollstaendig: {', '.join(missing)}")
    _require_exact_text(assets.get("schema_version"), "runtime_semantic_assets.schema_version", RUNTIME_SEMANTIC_ASSETS_SCHEMA_VERSION)
    release_id = _require_text(assets.get("release_id"), "runtime_semantic_assets.release_id")
    release_version = _require_text(assets.get("release_version"), "runtime_semantic_assets.release_version")
    release_fingerprint = _require_text(assets.get("release_fingerprint"), "runtime_semantic_assets.release_fingerprint")
    master_taxonomy_id = _require_text(assets.get("master_taxonomy_id"), "runtime_semantic_assets.master_taxonomy_id")
    master_taxonomy_version = _require_text(assets.get("master_taxonomy_version"), "runtime_semantic_assets.master_taxonomy_version")
    master_taxonomy_release_id = _require_optional_text(assets.get("master_taxonomy_release_id"), "runtime_semantic_assets.master_taxonomy_release_id")
    runtime_locale = _require_optional_text(assets.get("runtime_locale"), "runtime_semantic_assets.runtime_locale")
    if runtime_locale is not None and runtime_locale != "en":
        raise ValueError("runtime_semantic_assets.runtime_locale must be en.")
    _validate_projection_catalog(assets.get("projection_catalog"), release_id=release_id, release_version=release_version, release_fingerprint=release_fingerprint, master_taxonomy_id=master_taxonomy_id, master_taxonomy_version=master_taxonomy_version, master_taxonomy_release_id=master_taxonomy_release_id, runtime_locale=runtime_locale)
    _validate_vision_policy_bundle(assets.get("vision_policy_bundle"), release_fingerprint=release_fingerprint)
    return assets


def _validate_projection_catalog(payload: Any, *, release_id: str, release_version: str, release_fingerprint: str, master_taxonomy_id: str, master_taxonomy_version: str, master_taxonomy_release_id: str | None, runtime_locale: str | None) -> None:
    catalog = _require_dict(payload, "projection_catalog")
    missing = sorted(_PROJECTION_CATALOG_KEYS - set(catalog))
    if missing:
        raise ValueError(f"projection_catalog unvollstaendig: {', '.join(missing)}")
    _require_text(catalog.get("catalog_version"), "projection_catalog.catalog_version")
    if _require_text(catalog.get("release_id"), "projection_catalog.release_id") != release_id:
        raise ValueError("projection_catalog.release_id passt nicht zum Runtime-Bundle.")
    if _require_text(catalog.get("release_version"), "projection_catalog.release_version") != release_version:
        raise ValueError("projection_catalog.release_version passt nicht zum Runtime-Bundle.")
    if _require_text(catalog.get("release_fingerprint"), "projection_catalog.release_fingerprint") != release_fingerprint:
        raise ValueError("projection_catalog.release_fingerprint passt nicht zum Runtime-Bundle.")
    if _require_text(catalog.get("master_taxonomy_id"), "projection_catalog.master_taxonomy_id") != master_taxonomy_id:
        raise ValueError("projection_catalog.master_taxonomy_id passt nicht zum Runtime-Bundle.")
    if _require_text(catalog.get("master_taxonomy_version"), "projection_catalog.master_taxonomy_version") != master_taxonomy_version:
        raise ValueError("projection_catalog.master_taxonomy_version passt nicht zum Runtime-Bundle.")
    catalog_master_taxonomy_release_id = _require_optional_text(catalog.get("master_taxonomy_release_id"), "projection_catalog.master_taxonomy_release_id")
    if _optional_values_conflict(catalog_master_taxonomy_release_id, master_taxonomy_release_id):
        raise ValueError("projection_catalog.master_taxonomy_release_id passt nicht zum Runtime-Bundle.")
    catalog_runtime_locale = _require_optional_text(catalog.get("runtime_locale"), "projection_catalog.runtime_locale")
    if catalog_runtime_locale is not None and catalog_runtime_locale != "en":
        raise ValueError("projection_catalog.runtime_locale must be en.")
    if _optional_values_conflict(catalog_runtime_locale, runtime_locale):
        raise ValueError("projection_catalog.runtime_locale passt nicht zum Runtime-Bundle.")
    _require_list(catalog.get("projections"), "projection_catalog.projections")


def _validate_vision_policy_bundle(payload: Any, *, release_fingerprint: str) -> None:
    bundle = _require_dict(payload, "vision_policy_bundle")
    expected_keys = {"bundle_version", "release_fingerprint", "ocr_policy"}
    missing = sorted(expected_keys - set(bundle))
    if missing:
        raise ValueError(f"vision_policy_bundle unvollstaendig: {', '.join(missing)}")
    unknown = sorted(set(bundle) - expected_keys)
    if unknown:
        raise ValueError(f"vision_policy_bundle enthaelt unbekannte Felder: {', '.join(unknown)}")
    _require_exact_text(bundle.get("bundle_version"), "vision_policy_bundle.bundle_version", VISION_POLICY_BUNDLE_VERSION)
    if _require_text(bundle.get("release_fingerprint"), "vision_policy_bundle.release_fingerprint") != release_fingerprint:
        raise ValueError("vision_policy_bundle.release_fingerprint passt nicht zum Runtime-Bundle.")
    _validate_policy(bundle.get("ocr_policy"), "vision_policy_bundle.ocr_policy")


def _validate_policy(payload: Any, label: str) -> None:
    policy = _require_dict(payload, label)
    missing = sorted(_POLICY_KEYS - set(policy))
    if missing:
        raise ValueError(f"{label} unvollstaendig: {', '.join(missing)}")
    unknown = sorted(set(policy) - _POLICY_KEYS)
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Felder: {', '.join(unknown)}")
    _require_text(policy.get("policy_version"), f"{label}.policy_version")
    _require_text(policy.get("source_mode"), f"{label}.source_mode")
    defaults = _require_dict(policy.get("defaults"), f"{label}.defaults")
    _validate_ocr_defaults(defaults, f"{label}.defaults")


def _validate_ocr_defaults(payload: dict[str, Any], label: str) -> None:
    legacy_keys = sorted(_LEGACY_LOCAL_OCR_KEYS & set(payload))
    if legacy_keys:
        raise ValueError(f"{label} enthaelt lokale OCR-Altlasten: {', '.join(legacy_keys)}.")
    profile_id = _require_text(payload.get("profile_id"), f"{label}.profile_id")
    if profile_id not in _OCR_PROFILE_IDS:
        raise ValueError(f"{label}.profile_id ist ungueltig.")
    scan = _require_dict(payload.get("scan"), f"{label}.scan")
    _require_int(scan.get("min_chars_per_page"), f"{label}.scan.min_chars_per_page", minimum=1)
    _require_bool(scan.get("use_has_images"), f"{label}.scan.use_has_images")
    route = _require_dict(payload.get("vision_route"), f"{label}.vision_route")
    _require_bool(route.get("images_always_vision"), f"{label}.vision_route.images_always_vision")
    _require_bool(route.get("pdf_scans_use_vision"), f"{label}.vision_route.pdf_scans_use_vision")
    ocr_plugin = _require_dict(payload.get("ocr_plugin"), f"{label}.ocr_plugin")
    preferred_plugin = _require_text(ocr_plugin.get("preferred_plugin"), f"{label}.ocr_plugin.preferred_plugin")
    if preferred_plugin != _LLM_OCR_PLUGIN:
        raise ValueError(f"{label}.ocr_plugin.preferred_plugin muss {_LLM_OCR_PLUGIN} sein.")
    _require_bool(ocr_plugin.get("force_backup_on_scan"), f"{label}.ocr_plugin.force_backup_on_scan")
    render = _require_dict(payload.get("render"), f"{label}.render")
    _require_int(render.get("page_image_dpi"), f"{label}.render.page_image_dpi", minimum=72)
    _require_int(render.get("page_image_quality"), f"{label}.render.page_image_quality", minimum=1)
    _require_text(render.get("serializer_quality_mode"), f"{label}.render.serializer_quality_mode")
    _require_int(render.get("ocr_render_dpi"), f"{label}.render.ocr_render_dpi", minimum=72)


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return value


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text


def _require_optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, label)


def _require_exact_text(value: Any, label: str, expected: str) -> str:
    text = _require_text(value, label)
    if text != expected:
        raise ValueError(f"{label} muss {expected} sein.")
    return text


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return value


def _require_int(value: Any, label: str, *, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} fehlt oder ist ungueltig.") from None
    if parsed < minimum:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return parsed


def _optional_values_conflict(left: str | None, right: str | None) -> bool:
    return left != right and (left is not None or right is not None)
