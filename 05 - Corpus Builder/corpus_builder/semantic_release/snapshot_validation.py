"""Validation for embedded semantic release snapshot bundles."""

from __future__ import annotations

from typing import Any


def validate_embedded_release_bundle(release: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    projection_catalog = _require_dict(release.get("projection_catalog"), "release.projection_catalog")
    runtime_assets = _require_dict(release.get("runtime_semantic_assets"), "release.runtime_semantic_assets")
    release_id = _require_text(release.get("release_id"), "release.release_id")
    release_version = _require_text(release.get("release_version"), "release.release_version")
    fingerprint = _require_text(release.get("fingerprint"), "release.fingerprint")
    master_line = _require_text(release.get("master_taxonomy_release_id"), "release.master_taxonomy_release_id")
    runtime_locale = _require_text(release.get("runtime_locale"), "release.runtime_locale")
    _validate_release_header(projection_catalog, "projection_catalog", release_id, release_version, fingerprint, master_line, runtime_locale)
    _require_list(projection_catalog.get("projections"), "projection_catalog.projections")
    _validate_release_header(runtime_assets, "runtime_semantic_assets", release_id, release_version, fingerprint, master_line, runtime_locale)
    runtime_projection_catalog = _require_dict(runtime_assets.get("projection_catalog"), "runtime_semantic_assets.projection_catalog")
    _validate_release_header(
        runtime_projection_catalog,
        "runtime_semantic_assets.projection_catalog",
        release_id,
        release_version,
        fingerprint,
        master_line,
        runtime_locale,
    )
    return projection_catalog, runtime_assets


def _validate_release_header(
    payload: dict[str, Any],
    label: str,
    release_id: str,
    release_version: str,
    fingerprint: str,
    master_line: str,
    runtime_locale: str,
) -> None:
    _require_matching_text(payload.get("release_id"), f"{label}.release_id", release_id, f"{label}.release_id passt nicht zum Semantic Release.")
    _require_matching_text(payload.get("release_version"), f"{label}.release_version", release_version, f"{label}.release_version passt nicht zum Semantic Release.")
    _require_matching_text(payload.get("release_fingerprint"), f"{label}.release_fingerprint", fingerprint, f"{label}.release_fingerprint passt nicht zum Semantic Release.")
    _require_matching_text(payload.get("master_taxonomy_release_id"), f"{label}.master_taxonomy_release_id", master_line, f"{label}.master_taxonomy_release_id passt nicht zum Semantic Release.")
    _require_matching_text(payload.get("runtime_locale"), f"{label}.runtime_locale", runtime_locale, f"{label}.runtime_locale passt nicht zum Semantic Release.")


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


def _require_matching_text(value: Any, label: str, expected: str, mismatch_message: str) -> str:
    text = _require_text(value, label)
    if text != expected:
        raise ValueError(mismatch_message)
    return text
