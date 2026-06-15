from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..models.serialization import atomic_json_write, utc_now_iso
from ..runtime_semantic_assets import build_runtime_semantic_assets
from ..semantic_release import policy as release_policy
from ..taxonomy import SEMANTIC_RELEASE_SCHEMA_VERSION
from .control_language import control_locale_or_default
from .kernel_release_materialization_base import (
    DEFAULT_CUSTOM_RELEASE_VERSION,
    base_release_payload,
    canonical_texts,
    mapping,
    require_text,
)
from .kernel_release_materialization_projection import projection_payload, written_projection_refs


def materialize_candidate_release(payload: Mapping[str, Any]) -> dict[str, Any]:
    release_ref = mapping(payload, "release_ref")
    output_path = require_text(payload.get("output_path"), "output_path")
    base_release = base_release_payload(payload, release_ref=release_ref)
    projection_refs = [dict(item) for item in release_ref.get("projection_refs", []) if isinstance(item, Mapping)]
    if not release_ref or not projection_refs:
        raise ValueError("release_ref with projection_refs is required.")
    release_version = str(release_ref.get("release_version") or DEFAULT_CUSTOM_RELEASE_VERSION)
    precursors = [dict(item) for item in mapping(payload, "projection_update_state").get("projection_precursors", []) if isinstance(item, Mapping)]
    precursor_by_id = {str(item.get("projection_id") or ""): item for item in precursors}
    projections = [
        projection_payload(projection_ref=ref, precursor=precursor_by_id.get(str(ref.get("projection_id") or ""), {}), base_release=base_release)
        for ref in projection_refs
        if ref.get("projection_id")
    ]
    release = _release_payload(
        release_ref=release_ref,
        base_release=base_release,
        release_version=release_version,
        projections=projections,
        runtime_locale=control_locale_or_default(release_ref.get("runtime_locale"), payload.get("runtime_locale"), base_release.get("runtime_locale")),
    )
    release["analysis"] = release_policy.analyze_taxonomy_shape(release["master_taxonomy"], release["projections"])
    release["fingerprint"] = release_policy.build_release_fingerprint(release)
    release["release_fingerprint"] = release["fingerprint"]
    runtime_assets = build_runtime_semantic_assets(release).to_dict()
    release["projection_catalog"] = runtime_assets["projection_catalog"]
    release["runtime_semantic_assets"] = runtime_assets
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_write(path, release)
    return _materialization_result(path, release, release_ref, projection_refs)


def _release_payload(
    *,
    release_ref: Mapping[str, Any],
    base_release: Mapping[str, Any],
    release_version: str,
    projections: list[dict[str, Any]],
    runtime_locale: str,
) -> dict[str, Any]:
    return {
        "schema_version": str(base_release.get("schema_version") or SEMANTIC_RELEASE_SCHEMA_VERSION),
        "release_id": require_text(release_ref.get("release_id"), "release_ref.release_id"),
        "release_version": release_version,
        "master_taxonomy_id": require_text(base_release.get("master_taxonomy_id"), "base_release.master_taxonomy_id"),
        "master_taxonomy_version": require_text(base_release.get("master_taxonomy_version"), "base_release.master_taxonomy_version"),
        "master_taxonomy_release_id": str(base_release.get("master_taxonomy_release_id") or ""),
        "runtime_locale": runtime_locale,
        "projection_ids": canonical_texts([projection["projection_id"] for projection in projections]),
        "materialization_version": str(base_release.get("materialization_version") or "1"),
        "created_at": utc_now_iso(),
        "fingerprint": "",
        "master_taxonomy": mapping(base_release, "master_taxonomy"),
        "projections": sorted(projections, key=lambda item: (item["projection_id"].casefold(), item["projection_id"])),
    }


def _materialization_result(
    path: Path,
    release: Mapping[str, Any],
    release_ref: Mapping[str, Any],
    projection_refs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    written_ref = {
        "release_id": release["release_id"],
        "release_version": release["release_version"],
        "release_fingerprint": release["fingerprint"],
        "taxonomy_ref": dict(release_ref.get("taxonomy_ref") or {}),
        "projection_refs": written_projection_refs(list(release["projections"]), projection_refs),
        "runtime_locale": release["runtime_locale"],
    }
    return {
        "output_path": str(path),
        "release_path": str(path),
        "release_id": release["release_id"],
        "release_version": release["release_version"],
        "release_fingerprint": release["fingerprint"],
        "projection_ids": list(release["projection_ids"]),
        "taxonomy_ref": written_ref["taxonomy_ref"],
        "release_ref": written_ref,
    }
