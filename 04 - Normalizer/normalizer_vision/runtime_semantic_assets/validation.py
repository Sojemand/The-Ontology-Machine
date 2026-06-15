"""Strict validation for runtime semantic asset contracts."""
from __future__ import annotations

from typing import Any

from ..taxonomy.surface_signals import projection_surface_signals
from .semantic_policy_validation import validate_semantic_extraction_policy

REQUIRED_RELEASE_KEYS = frozenset({"release_id", "release_version", "master_taxonomy_id", "master_taxonomy_version", "projection_ids", "materialization_version", "fingerprint", "master_taxonomy", "projections"})
REQUIRED_RUNTIME_KEYS = frozenset({"schema_version", "release_id", "release_version", "release_fingerprint", "master_taxonomy_id", "master_taxonomy_version", "promotion_slots", "projection_catalog", "vision_policy_bundle"})
_OCR_PROFILE_IDS = frozenset({"layout_fidelity_v1", "balanced_text_v1"})
_LLM_OCR_PLUGIN = "optimizer-llm-ocr"
_LEGACY_LOCAL_OCR_KEYS = frozenset({"device_policy", "paddlevl"})


def validate_release_payload(payload: Any) -> dict[str, Any]:
    release = _require_dict(payload, "release")
    missing = sorted(REQUIRED_RELEASE_KEYS - set(release))
    if missing:
        raise ValueError(f"Semantic Release unvollstaendig: {', '.join(missing)}")
    expected_ids = _require_projection_id_list(release.get("projection_ids"), "projection_ids")
    if expected_ids != _canonical_projection_id_list(expected_ids):
        raise ValueError("projection_ids muss kanonisch nach projection_id sortiert sein.")
    found_ids = [_validate_projection_payload(item, index) for index, item in enumerate(_require_list(release.get("projections"), "projections"))]
    if expected_ids and expected_ids != found_ids:
        missing_ids = sorted(set(expected_ids) - set(found_ids))
        extra_ids = sorted(set(found_ids) - set(expected_ids))
        parts = []
        if missing_ids:
            parts.append(f"fehlende Projection-Payloads: {', '.join(missing_ids)}")
        if extra_ids:
            parts.append(f"unerwartete Projection-Payloads: {', '.join(extra_ids)}")
        if not parts:
            parts.append("Projection-Payload-Reihenfolge muss projection_ids exakt entsprechen.")
        raise ValueError("Semantic Release Projection-Mismatch: " + "; ".join(parts))
    _require_text(release.get("release_id"), "release_id")
    _require_text(release.get("release_version"), "release_version")
    _require_text(release.get("master_taxonomy_id"), "master_taxonomy_id")
    _require_text(release.get("master_taxonomy_version"), "master_taxonomy_version")
    _require_text(release.get("fingerprint"), "fingerprint")
    _require_dict(release.get("master_taxonomy"), "master_taxonomy")
    _require_optional_text(release.get("master_taxonomy_release_id"), "master_taxonomy_release_id")
    _require_optional_text(release.get("runtime_locale"), "runtime_locale")
    return release


def validate_runtime_semantic_assets(payload: Any) -> dict[str, Any]:
    runtime_assets = _require_dict(payload, "runtime_semantic_assets")
    missing = sorted(REQUIRED_RUNTIME_KEYS - set(runtime_assets))
    if missing:
        raise ValueError(f"runtime_semantic_assets unvollstaendig: {', '.join(missing)}")
    release_fingerprint = _require_text(runtime_assets.get("release_fingerprint"), "release_fingerprint")
    projection_catalog = _require_dict(runtime_assets.get("projection_catalog"), "projection_catalog")
    vision_policy_bundle = _require_dict(runtime_assets.get("vision_policy_bundle"), "vision_policy_bundle")
    if _require_text(projection_catalog.get("release_fingerprint"), "projection_catalog.release_fingerprint") != release_fingerprint:
        raise ValueError("projection_catalog.release_fingerprint passt nicht zum Runtime-Bundle.")
    if _require_text(vision_policy_bundle.get("release_fingerprint"), "vision_policy_bundle.release_fingerprint") != release_fingerprint:
        raise ValueError("vision_policy_bundle.release_fingerprint passt nicht zum Runtime-Bundle.")
    _require_text(projection_catalog.get("catalog_version"), "projection_catalog.catalog_version")
    _require_text(vision_policy_bundle.get("bundle_version"), "vision_policy_bundle.bundle_version")
    master_taxonomy_release_id = _require_optional_text(runtime_assets.get("master_taxonomy_release_id"), "master_taxonomy_release_id")
    catalog_master_taxonomy_release_id = _require_optional_text(projection_catalog.get("master_taxonomy_release_id"), "projection_catalog.master_taxonomy_release_id")
    if master_taxonomy_release_id and catalog_master_taxonomy_release_id and catalog_master_taxonomy_release_id != master_taxonomy_release_id:
        raise ValueError("projection_catalog.master_taxonomy_release_id passt nicht zum Runtime-Bundle.")
    runtime_locale = _require_optional_text(runtime_assets.get("runtime_locale"), "runtime_locale")
    catalog_runtime_locale = _require_optional_text(projection_catalog.get("runtime_locale"), "projection_catalog.runtime_locale")
    if runtime_locale and catalog_runtime_locale and catalog_runtime_locale != runtime_locale:
        raise ValueError("projection_catalog.runtime_locale passt nicht zum Runtime-Bundle.")
    _validate_policy(vision_policy_bundle.get("ocr_policy"), "vision_policy_bundle.ocr_policy")
    _validate_policy(vision_policy_bundle.get("semantic_extraction_policy"), "vision_policy_bundle.semantic_extraction_policy")
    _require_list(runtime_assets.get("promotion_slots"), "promotion_slots")
    for index, projection in enumerate(_require_list(projection_catalog.get("projections"), "projection_catalog.projections")):
        _require_dict(projection, f"projection_catalog.projections[{index}]")
        _require_list(projection.get("promotion_rules"), f"projection_catalog.projections[{index}].promotion_rules")
        _require_dict(projection.get("field_slot_map"), f"projection_catalog.projections[{index}].field_slot_map")
    return runtime_assets


def _validate_projection_payload(payload: Any, index: int) -> str:
    projection = _require_dict(payload, f"projections[{index}]")
    projection_id = _require_text(projection.get("projection_id"), f"projections[{index}].projection_id")
    _require_text(projection.get("label"), f"projections[{index}].label")
    routing = _require_dict(projection.get("routing"), f"projections[{index}].routing")
    _require_text(routing.get("when_to_use"), f"projections[{index}].routing.when_to_use")
    _require_text(routing.get("avoid_when"), f"projections[{index}].routing.avoid_when")
    examples = _require_list(routing.get("example_document_types"), f"projections[{index}].routing.example_document_types")
    if not [_require_text(item, f"projections[{index}].routing.example_document_types[]") for item in examples]:
        raise ValueError(f"projections[{index}].routing.example_document_types darf nicht leer sein.")
    projection_surface_signals(projection, required=True, field_name=f"projections[{index}].routing.surface_signals")
    return projection_id


def _validate_policy(payload: Any, label: str) -> None:
    policy = _require_dict(payload, label)
    _require_text(policy.get("policy_version"), f"{label}.policy_version")
    _require_text(policy.get("source_mode"), f"{label}.source_mode")
    defaults = _require_dict(policy.get("defaults"), f"{label}.defaults")
    if label.endswith(".ocr_policy"):
        if "projection_overrides" in policy:
            raise ValueError(f"{label}.projection_overrides gehoert nicht in die OCR-Policy.")
        _validate_ocr_defaults(defaults, f"{label}.defaults")
        return
    _require_dict(policy.get("projection_overrides"), f"{label}.projection_overrides")
    validate_semantic_extraction_policy(policy, label)


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
    vision_route = _require_dict(payload.get("vision_route"), f"{label}.vision_route")
    _require_bool(vision_route.get("images_always_vision"), f"{label}.vision_route.images_always_vision")
    _require_bool(vision_route.get("pdf_scans_use_vision"), f"{label}.vision_route.pdf_scans_use_vision")
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


def _require_projection_id_list(value: Any, label: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(_require_list(value, label)):
        projection_id = _require_text(item, f"{label}[{index}]")
        key = projection_id.casefold()
        if key in seen:
            raise ValueError(f"{label}[{index}] enthaelt eine doppelte Projection-ID.")
        seen.add(key)
        result.append(projection_id)
    return result


def _canonical_projection_id_list(values: list[str]) -> list[str]:
    return sorted(values, key=lambda item: (item.casefold(), item))


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text


def _require_optional_text(value: Any, label: str) -> str | None:
    if value in (None, ""):
        return None
    return _require_text(value, label)


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
