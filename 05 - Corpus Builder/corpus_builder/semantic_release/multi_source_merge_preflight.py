from __future__ import annotations

from typing import Any, Mapping

from .multi_source_merge_manifests import (
    artifact_ref,
    artifact_root_for_merge_manifest_root,
    manifest_fingerprint,
    merge_manifest_root,
    utc_iso,
    write_manifest,
)
from .multi_source_merge_policy import build_collision_summary
from .multi_source_merge_sql import id_map_mappings
from .multi_source_merge_types import owner_ok, path_hash
from .multi_source_merge_validation import classify_sources, validate_merge_selection, validate_target_identity


def multi_source_merge_preflight(payload: Mapping[str, Any]) -> dict[str, Any]:
    selection = payload.get("selection", payload)
    if not isinstance(selection, Mapping):
        raise ValueError("selection is required.")
    sources = validate_merge_selection(selection)
    target_identity = {
        "merge_run_id": str(selection.get("merge_run_id", "")),
        "source_database_ids": [str(item.get("source_database_id") or "") for item in sources],
        "target_database_path_hash": path_hash(str(selection.get("target_database_path", ""))),
    }
    validate_target_identity(selection, _mapping(payload, "target_identity") or target_identity)

    source_class, mixed = classify_sources(sources)
    manifest_root = merge_manifest_root(str(selection.get("target_artifact_root", "")), str(selection.get("merge_run_id", "")))
    artifact_root = artifact_root_for_merge_manifest_root(manifest_root)
    selection_path = manifest_root / "merge_selection.json"
    collision_manifest_path = manifest_root / "merge_collision_manifest.json"
    write_manifest(selection_path, dict(selection))

    collisions: list[dict[str, Any]] = []
    collision_manifest = {
        "schema_version": "kernel.database_merge_collision_manifest.v1",
        "merge_run_id": str(selection.get("merge_run_id", "")),
        "merge_route": str(selection.get("merge_route") or "database_merge_additive_only"),
        "created_at": utc_iso(),
        "updated_at": utc_iso(),
        "source_databases": sources,
        "target_artifact_root": str(selection.get("target_artifact_root", "")),
        "target_database_path": str(selection.get("target_database_path", "")),
        "duplicate_policy": str(selection.get("duplicate_policy") or "keep_all"),
        "collisions": collisions,
        "resolution_summary": build_collision_summary(collisions),
        "manifest_revision": 1,
    }
    collision_manifest["manifest_fingerprint"] = manifest_fingerprint(collision_manifest)
    write_manifest(collision_manifest_path, collision_manifest)

    output = {
        "source_class": source_class,
        "is_mixed_source_class": mixed,
        "merge_selection_ref": artifact_ref(selection_path, artifact_root),
        "collision_manifest_ref": artifact_ref(collision_manifest_path, artifact_root),
        "collision_summary": dict(collision_manifest["resolution_summary"]),
        "required_user_choices": [],
        "id_map_preview_ref": {},
        "preflight_fingerprint": collision_manifest["manifest_fingerprint"],
    }
    if source_class == "filled":
        preview_mappings = id_map_mappings(selection)
        preview_path = manifest_root / "merge_id_map_preview.json"
        preview_payload = {
            "schema_version": "kernel.database_merge_id_map.v1",
            "merge_run_id": str(selection.get("merge_run_id", "")),
            "created_at": utc_iso(),
            "source_databases": sources,
            "target_database_path": str(selection.get("target_database_path", "")),
            "mappings": preview_mappings,
            "record_count": len(preview_mappings),
        }
        preview_payload["map_fingerprint"] = manifest_fingerprint(preview_payload)
        write_manifest(preview_path, preview_payload)
        output["id_map_preview_ref"] = artifact_ref(preview_path, artifact_root)
    return owner_ok(
        owner_action="multi_source_merge_preflight",
        capability="multi_source_merge_domain_service",
        target_identity=target_identity,
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "multi_source_merge_preflight",
            "merge_run_id": str(selection.get("merge_run_id", "")),
            "target_database_path_hash": target_identity["target_database_path_hash"],
        },
    )


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}
