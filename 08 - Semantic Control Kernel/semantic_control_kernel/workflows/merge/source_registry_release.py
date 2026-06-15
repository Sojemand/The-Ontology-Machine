from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.workflows.merge.source_registry_errors import MergeSourceResolutionError


def release_identity_from_artifact_tree(artifact_root: str) -> dict[str, Any]:
    release_json = single_complete_release_json(Path(artifact_root))
    try:
        payload = json.loads(release_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MergeSourceResolutionError(f"Source Semantic Release package cannot be read: {release_json}") from exc
    release_id = first_text(payload, "release_id", "semantic_release.release_id", "runtime_semantic_assets.release_id")
    release_version = first_text(payload, "release_version", "semantic_release.release_version", "runtime_semantic_assets.release_version")
    release_fingerprint = first_text(
        payload,
        "release_fingerprint",
        "fingerprint",
        "projection_catalog.release_fingerprint",
        "runtime_semantic_assets.release_fingerprint",
        "semantic_release.release_fingerprint",
    )
    if not release_id or not release_version or not release_fingerprint:
        raise MergeSourceResolutionError(f"Source Semantic Release package is incomplete and cannot be merged: {release_json}")
    release_ref = release_ref_from_payload(
        payload,
        release_id=release_id,
        release_version=release_version,
        release_fingerprint=release_fingerprint,
    )
    return {
        "release_fingerprint": release_fingerprint,
        "release_id": release_id,
        "release_path": str(release_json.parent),
        "release_ref": release_ref,
        "release_version": release_version,
    }


def release_ref_from_payload(payload: Mapping[str, Any], *, release_id: str, release_version: str, release_fingerprint: str) -> dict[str, Any]:
    release_ref = nested_mapping(payload, "release_ref")
    if not release_ref:
        release_ref = {
            "release_fingerprint": release_fingerprint,
            "release_id": release_id,
            "release_version": release_version,
        }
    release_ref.setdefault("release_id", release_id)
    release_ref.setdefault("release_version", release_version)
    release_ref.setdefault("release_fingerprint", release_fingerprint)
    taxonomy_ref = taxonomy_ref_from_release_payload(payload, release_ref=release_ref)
    projection_refs = projection_refs_from_release_payload(payload, release_ref=release_ref)
    if taxonomy_ref:
        release_ref["taxonomy_ref"] = taxonomy_ref
    if projection_refs:
        release_ref["projection_refs"] = projection_refs
    runtime_locale = first_text(payload, "runtime_locale", "projection_catalog.runtime_locale", "runtime_semantic_assets.runtime_locale")
    if runtime_locale:
        release_ref.setdefault("runtime_locale", runtime_locale)
    return release_ref


def taxonomy_ref_from_release_payload(payload: Mapping[str, Any], *, release_ref: Mapping[str, Any]) -> dict[str, Any]:
    taxonomy_ref = nested_mapping(payload, "taxonomy_ref") or nested_mapping(release_ref, "taxonomy_ref")
    master_taxonomy = nested_mapping(payload, "master_taxonomy")
    if taxonomy_ref:
        taxonomy_ref = deepcopy(taxonomy_ref)
    elif master_taxonomy:
        taxonomy_ref = {}
    else:
        return {}
    taxonomy_id = first_text(taxonomy_ref, "taxonomy_id") or first_text(master_taxonomy, "taxonomy_id") or first_text(payload, "master_taxonomy_id")
    taxonomy_version = first_text(taxonomy_ref, "taxonomy_version") or first_text(master_taxonomy, "taxonomy_version") or first_text(payload, "master_taxonomy_version")
    taxonomy_fingerprint = first_text(taxonomy_ref, "taxonomy_fingerprint") or first_text(payload, "master_taxonomy_release_id") or first_text(payload, "taxonomy_fingerprint")
    runtime_locale = first_text(taxonomy_ref, "runtime_locale") or first_text(payload, "runtime_locale", "projection_catalog.runtime_locale")
    for key, value in (
        ("taxonomy_id", taxonomy_id),
        ("taxonomy_version", taxonomy_version),
        ("taxonomy_fingerprint", taxonomy_fingerprint),
        ("runtime_locale", runtime_locale),
    ):
        if value:
            taxonomy_ref.setdefault(key, value)
    if master_taxonomy and not isinstance(taxonomy_ref.get("master_taxonomy"), Mapping):
        taxonomy_ref["master_taxonomy"] = deepcopy(master_taxonomy)
    return taxonomy_ref


def projection_refs_from_release_payload(payload: Mapping[str, Any], *, release_ref: Mapping[str, Any]) -> list[dict[str, Any]]:
    existing_refs = release_ref.get("projection_refs")
    if not isinstance(existing_refs, list):
        existing_refs = payload.get("projection_refs")
    projections = [dict(item) for item in payload.get("projections", []) if isinstance(item, Mapping)] if isinstance(payload.get("projections"), list) else []
    projections_by_id = {str(item.get("projection_id") or ""): item for item in projections if item.get("projection_id")}
    if isinstance(existing_refs, list) and existing_refs:
        return [
            enrich_projection_ref(dict(item), projections_by_id.get(str(item.get("projection_id") or "")))
            for item in existing_refs
            if isinstance(item, Mapping)
        ]
    return [projection_ref_from_projection_payload(item) for item in projections if item.get("projection_id")]


def enrich_projection_ref(projection_ref: dict[str, Any], projection_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if projection_payload:
        projection_ref.setdefault("projection_fingerprint", str(projection_payload.get("projection_fingerprint") or ""))
        projection_ref.setdefault("included_taxonomy_codes", included_taxonomy_codes(projection_payload))
        projection_ref.setdefault("projection_payload", deepcopy(dict(projection_payload)))
    return projection_ref


def projection_ref_from_projection_payload(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "included_taxonomy_codes": included_taxonomy_codes(projection),
        "projection_fingerprint": str(projection.get("projection_fingerprint") or ""),
        "projection_id": str(projection.get("projection_id") or ""),
        "projection_payload": deepcopy(dict(projection)),
    }


def included_taxonomy_codes(projection: Mapping[str, Any]) -> list[str]:
    codes: set[str] = set()
    for key in ("domain_ids", "include_document_types", "include_categories", "include_subcategories", "include_field_codes", "include_row_types", "include_cell_codes"):
        values = projection.get(key)
        if isinstance(values, list):
            codes.update(str(item).strip() for item in values if str(item).strip())
    return sorted(codes)


def single_complete_release_json(artifact_root: Path) -> Path:
    releases = artifact_root / "Semantic Release" / "releases"
    candidates = sorted(path.resolve(strict=False) for path in releases.glob("*/release.json") if path.is_file())
    if not candidates:
        raise MergeSourceResolutionError(f"Source Artifact Tree has no complete Semantic Release package: {artifact_root}")
    if len(candidates) == 1:
        return candidates[0]
    non_default = [path for path in candidates if path.parent.name != "semantic_release.default"]
    if len(non_default) == 1:
        return non_default[0]
    pool = non_default or candidates
    return max(pool, key=lambda path: (path.stat().st_mtime_ns, path.as_posix()))


def first_text(payload: Mapping[str, Any], *paths: str) -> str:
    for path in paths:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
        text = str(current or "").strip()
        if text:
            return text
    return ""


def nested_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["release_identity_from_artifact_tree"]
