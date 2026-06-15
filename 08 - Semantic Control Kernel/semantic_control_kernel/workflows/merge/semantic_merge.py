from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.workflows.merge.collision_manifest import build_collision_manifest
from semantic_control_kernel.workflows.merge.receipts import adapter_output, blocker_from_adapter_result


def merge_taxonomy_and_projections_additive(
    merge_adapter: object,
    *,
    selection: Mapping[str, Any],
    merge_result: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, MergeWorkflowBlocker | None, object | None]:
    result = merge_adapter.merge_semantic_release_candidates(
        {
            "merge_run_id": str(selection.get("merge_run_id") or ""),
            "merge_result": dict(merge_result or {}),
            "projection_merge_mode": str(selection.get("projection_merge_mode") or ""),
            "selection": dict(selection),
            "source_releases": [
                _source_release_ref(source)
                for source in selection.get("source_databases", [])
                if isinstance(source, Mapping)
            ],
        }
    )
    blocker = blocker_from_adapter_result("building_collision_manifest", result, function_name="merge_taxonomy_and_projections_additive")
    if blocker is not None:
        return None, blocker, result
    output = adapter_output(result)
    collisions = output.get("collisions", [])
    try:
        manifest = build_collision_manifest(
            merge_run_id=str(selection["merge_run_id"]),
            merge_route=str(selection["merge_route"]),
            source_databases=list(selection["source_databases"]),
            target_artifact_root=str(selection["target_artifact_root"]),
            target_database_path=str(selection["target_database_path"]),
            collisions=[dict(item) for item in collisions if isinstance(item, Mapping)],
        ).to_dict()
    except ValueError as exc:
        return None, MergeWorkflowBlocker(
            blocker_code="invalid_owner_response",
            step_id="building_collision_manifest",
            function_or_route="merge_taxonomy_and_projections_additive",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Merge owner returned collision evidence that failed Kernel validation.",
            diagnostics=({"reason": str(exc)},),
        ), result
    semantic_package = dict(output.get("semantic_merge_package", {})) if isinstance(output.get("semantic_merge_package"), Mapping) else {}
    taxonomy_ref = _mapping(output.get("reconciled_taxonomy_ref")) or _mapping(semantic_package.get("taxonomy_ref"))
    projection_refs = _mapping_list(output.get("reconciled_projection_refs")) or _mapping_list(semantic_package.get("projection_refs"))
    if taxonomy_ref:
        semantic_package["taxonomy_ref"] = taxonomy_ref
    if projection_refs:
        semantic_package["projection_refs"] = projection_refs
    release_identity_policy = _mapping(output.get("release_identity_policy")) or _mapping(semantic_package.get("release_identity_policy"))
    if release_identity_policy:
        semantic_package["release_identity_policy"] = release_identity_policy
    target_semantic_release_folder = str(output.get("target_semantic_release_folder", "")).strip()
    if target_semantic_release_folder:
        semantic_package["target_semantic_release_folder"] = target_semantic_release_folder
    return {"collision_manifest": manifest, "semantic_merge_package": semantic_package}, None, result


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _source_release_ref(source: Mapping[str, Any]) -> dict[str, Any]:
    release_ref = dict(source.get("source_release_ref") or {}) if isinstance(source.get("source_release_ref"), Mapping) else {}
    release_ref.setdefault("source_database_id", source.get("source_database_id"))
    release_ref.setdefault("semantic_release_id", source.get("source_semantic_release_id"))
    release_ref.setdefault("semantic_release_version", source.get("source_semantic_release_version"))
    release_ref.setdefault("release_id", source.get("source_semantic_release_id"))
    release_ref.setdefault("release_version", source.get("source_semantic_release_version"))
    release_ref.setdefault("release_fingerprint", source.get("source_release_fingerprint"))
    return release_ref
