from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .kernel_candidate import stable_hash
from .kernel_merge_common import collision, projection_merge_mode as normalize_projection_merge_mode
from .kernel_merge_projection import merge_projection_refs_to_single
from .kernel_merge_taxonomy import merge_taxonomy_refs


def merge_candidates(
    *,
    merge_run_id: str,
    source_release_refs: Sequence[Mapping[str, Any]],
    projection_merge_mode: str = "preserve_source_projections",
) -> dict[str, Any]:
    collisions: list[dict[str, Any]] = []
    seen_taxonomies: dict[str, str] = {}
    seen_projections: dict[str, dict[str, Any]] = {}
    projection_refs: list[dict[str, Any]] = []
    taxonomy_refs: list[dict[str, Any]] = []
    mode = normalize_projection_merge_mode(projection_merge_mode)
    for release in source_release_refs:
        _collect_taxonomy_ref(release, seen_taxonomies, taxonomy_refs, collisions, merge_run_id)
        _collect_projection_refs(release, seen_projections, projection_refs, collisions, merge_run_id, mode)
    reconciled_taxonomy_ref = merge_taxonomy_refs(taxonomy_refs, merge_run_id=merge_run_id)
    reconciled_projection_refs = (
        merge_projection_refs_to_single(projection_refs, taxonomy_ref=reconciled_taxonomy_ref, merge_run_id=merge_run_id)
        if mode == "merge_to_single_projection"
        else projection_refs
    )
    semantic_merge_package = {
        "merge_run_id": merge_run_id,
        "projection_merge_mode": mode,
        "projection_refs": reconciled_projection_refs,
        "release_fingerprint": stable_hash(repr((merge_run_id, mode, source_release_refs))),
        "source_release_count": len(source_release_refs),
        "taxonomy_ref": reconciled_taxonomy_ref,
    }
    semantic_merge_fingerprint = stable_hash(repr(semantic_merge_package))
    return {
        "semantic_merge_package_ref": {"artifact_path": f"merge/{merge_run_id}/semantic_merge_package.json"},
        "semantic_collision_manifest_ref": {"artifact_path": f"merge/{merge_run_id}/semantic_collision_manifest.json"},
        "reconciled_taxonomy_ref": reconciled_taxonomy_ref,
        "reconciled_projection_refs": reconciled_projection_refs,
        "semantic_merge_fingerprint": semantic_merge_fingerprint,
        "unresolved_collision_count": sum(1 for item in collisions if item["requires_user_choice"]),
        "collisions": collisions,
        "semantic_merge_package": semantic_merge_package,
    }


def _collect_taxonomy_ref(
    release: Mapping[str, Any],
    seen_taxonomies: dict[str, str],
    taxonomy_refs: list[dict[str, Any]],
    collisions: list[dict[str, Any]],
    merge_run_id: str,
) -> None:
    taxonomy = release.get("taxonomy_ref", {})
    if not isinstance(taxonomy, Mapping):
        return
    taxonomy_id = str(taxonomy.get("taxonomy_id", ""))
    fingerprint = str(taxonomy.get("taxonomy_fingerprint", ""))
    if taxonomy_id and taxonomy_id in seen_taxonomies and seen_taxonomies[taxonomy_id] != fingerprint:
        collisions.append(collision("taxonomy_fingerprint_collision", merge_run_id, taxonomy_id, release))
    seen_taxonomies[taxonomy_id] = fingerprint
    if taxonomy:
        taxonomy_refs.append(deepcopy(dict(taxonomy)))


def _collect_projection_refs(
    release: Mapping[str, Any],
    seen_projections: dict[str, dict[str, Any]],
    projection_refs: list[dict[str, Any]],
    collisions: list[dict[str, Any]],
    merge_run_id: str,
    mode: str,
) -> None:
    for projection in release.get("projection_refs", []):
        if not isinstance(projection, Mapping):
            continue
        projection_id = str(projection.get("projection_id", ""))
        fingerprint = str(projection.get("projection_fingerprint", ""))
        previous = seen_projections.get(projection_id)
        if mode == "preserve_source_projections" and projection_id and previous and str(previous.get("projection_fingerprint", "")) != fingerprint:
            collisions.append(collision("projection_fingerprint_collision", merge_run_id, projection_id, projection))
        if projection_id and previous and str(previous.get("projection_fingerprint", "")) == fingerprint:
            continue
        projection_ref = deepcopy(dict(projection))
        seen_projections[projection_id] = projection_ref
        projection_refs.append(projection_ref)
