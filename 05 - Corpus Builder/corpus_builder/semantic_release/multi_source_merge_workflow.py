from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .multi_source_merge_artifacts import (
    artifact_path_mappings,
    cleanup_staged_artifacts,
    promote_staged_artifact_mappings,
    stage_artifact_mappings,
)
from .multi_source_merge_manifests import (
    artifact_ref,
    artifact_root_for_merge_manifest_root,
    load_manifest,
    manifest_fingerprint,
    merge_manifest_root,
    utc_iso,
    write_manifest,
)
from .multi_source_merge_policy import build_collision_summary
from .multi_source_merge_sql import id_map_mappings, merge_sql_databases
from .multi_source_merge_types import owner_ok, path_hash
from .multi_source_merge_validation import classify_sources, validate_artifact_path_within_root, validate_merge_selection, validate_target_identity


def multi_source_merge_databases(payload: Mapping[str, Any]) -> dict[str, Any]:
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

    source_class, _mixed = classify_sources(sources)
    merge_mode = _merge_mode_for_sources(payload, source_class)

    manifest_root = merge_manifest_root(str(selection.get("target_artifact_root", "")), str(selection.get("merge_run_id", "")))
    artifact_root = artifact_root_for_merge_manifest_root(manifest_root)
    collision_manifest = _load_collision_manifest(payload, manifest_root)
    collisions = [dict(item) for item in collision_manifest.get("collisions", []) if isinstance(item, Mapping)]
    if any(item.get("resolution_status") in {"unresolved", "requires_user_choice"} for item in collisions):
        raise ValueError("unresolved_merge_collision: collision manifest still contains unresolved collisions.")

    mappings = id_map_mappings(selection) if merge_mode == "filled_sql_and_artifacts" else []
    artifact_mappings = artifact_path_mappings(selection, mappings)
    artifact_copy_report: dict[str, Any] = {"copied_artifact_count": 0, "copied_artifact_mappings": []}
    artifact_stage_report: dict[str, Any] = {"staged_artifact_count": 0, "staged_artifact_mappings": []}
    artifact_stage_manifest_path = manifest_root / "artifact_stage_manifest.json"
    artifact_stage_manifest_ref: dict[str, str] = {}
    sql_mutation_report: dict[str, Any] = {
        "written_database_path": str(selection.get("target_database_path", "")),
        "copied_document_count": 0,
        "post_merge_counts": {"documents": 0, "embeddings": 0},
    }
    if merge_mode == "filled_sql_and_artifacts":
        staging_root = manifest_root / "artifact_staging"
        artifact_stage_report = stage_artifact_mappings(artifact_mappings, staging_root)
        artifact_stage_manifest_ref = artifact_ref(artifact_stage_manifest_path, artifact_root)
        _write_artifact_stage_manifest(
            artifact_stage_manifest_path,
            selection=selection,
            status="staged",
            stage_report=artifact_stage_report,
        )
        try:
            sql_mutation_report = merge_sql_databases(selection, mappings)
        except Exception as exc:
            cleanup_report = cleanup_staged_artifacts(staging_root)
            _write_artifact_stage_manifest(
                artifact_stage_manifest_path,
                selection=selection,
                status="sql_failed_staging_cleanup",
                stage_report=artifact_stage_report,
                cleanup_report=cleanup_report,
                error=str(exc),
            )
            raise
        try:
            artifact_copy_report = promote_staged_artifact_mappings(artifact_stage_report["staged_artifact_mappings"])
        except Exception as exc:
            _write_artifact_stage_manifest(
                artifact_stage_manifest_path,
                selection=selection,
                status="promote_failed_recovery_available",
                stage_report=artifact_stage_report,
                sql_mutation_report=sql_mutation_report,
                error=str(exc),
            )
            raise
        cleanup_report = cleanup_staged_artifacts(staging_root)
        _write_artifact_stage_manifest(
            artifact_stage_manifest_path,
            selection=selection,
            status="promoted",
            stage_report=artifact_stage_report,
            sql_mutation_report=sql_mutation_report,
            artifact_copy_report=artifact_copy_report,
            cleanup_report=cleanup_report,
        )
        artifact_mappings = list(artifact_copy_report["copied_artifact_mappings"])
    merge_package_path = manifest_root / "merge_package.json"
    merge_package = {
        "schema_version": "kernel.multi_source_merge_package.v1",
        "merge_run_id": str(selection.get("merge_run_id", "")),
        "created_at": utc_iso(),
        "mode": merge_mode,
        "source_databases": sources,
        "target_database_path": str(selection.get("target_database_path", "")),
        "collision_manifest_ref": artifact_ref(manifest_root / "merge_collision_manifest.json", artifact_root),
        "artifact_stage_manifest_ref": artifact_stage_manifest_ref,
        "id_map_record_count": len(mappings),
        "artifact_path_mapping_count": len(artifact_mappings),
        "collision_summary": build_collision_summary(collisions),
        "sql_mutation_report": sql_mutation_report,
        "artifact_copy_report": _compact_artifact_copy_report(artifact_copy_report),
        "artifact_stage_report": _compact_artifact_stage_report(artifact_stage_report),
    }
    merge_package["merge_package_fingerprint"] = manifest_fingerprint(merge_package)
    write_manifest(merge_package_path, merge_package)

    output = {
        "merge_package_ref": artifact_ref(merge_package_path, artifact_root),
        "merge_id_map_ref": {},
        "written_database_ref": {"database_path": str(selection.get("target_database_path", ""))},
        "artifact_map_ref": {},
        "record_counts": {"records": len(mappings), **dict(sql_mutation_report.get("post_merge_counts", {}))},
        "materialization_preservation_report_ref": {},
        "id_map_record_count": len(mappings),
        "artifact_path_mapping_count": len(artifact_mappings),
        "sql_mutation_report": sql_mutation_report,
        "artifact_copy_report": _compact_artifact_copy_report(artifact_copy_report),
        "artifact_stage_manifest_ref": artifact_stage_manifest_ref,
        "artifact_stage_report": _compact_artifact_stage_report(artifact_stage_report),
        "backfill_required": bool(mappings),
    }

    if merge_mode == "filled_sql_and_artifacts":
        id_map_path = manifest_root / "merge_id_map.json"
        id_map_payload = {
            "schema_version": "kernel.database_merge_id_map.v1",
            "merge_run_id": str(selection.get("merge_run_id", "")),
            "created_at": utc_iso(),
            "source_databases": sources,
            "target_database_path": str(selection.get("target_database_path", "")),
            "mappings": mappings,
            "record_count": len(mappings),
        }
        id_map_payload["map_fingerprint"] = manifest_fingerprint(id_map_payload)
        write_manifest(id_map_path, id_map_payload)

        artifact_map_path = manifest_root / "artifact_path_map.json"
        write_manifest(
            artifact_map_path,
            {
                "schema_version": "kernel.database_merge_artifact_map.v1",
                "merge_run_id": str(selection.get("merge_run_id", "")),
                "source_databases": sources,
                "target_artifact_root": str(selection.get("target_artifact_root", "")),
                "mappings": artifact_mappings,
                "copy_report": artifact_copy_report,
            },
        )

        preservation_path = manifest_root / "materialization_preservation_report.json"
        preservation_payload = {
            "schema_version": "kernel.materialization_preservation_report.v1",
            "merge_run_id": str(selection.get("merge_run_id", "")),
            "source_database_ids": target_identity["source_database_ids"],
            "preserved_pipeline_batch_ids": [item["source_pipeline_batch_id"] for item in mappings],
            "preserved_release_fingerprints": [item["release_fingerprint"] for item in mappings],
            "preserved_projection_fingerprints": [item["projection_fingerprint"] for item in mappings],
            "preserved_taxonomy_fingerprints": [item["taxonomy_fingerprint"] for item in mappings],
            "copied_document_count": sql_mutation_report["copied_document_count"],
            "copied_artifact_count": artifact_copy_report["copied_artifact_count"],
        }
        write_manifest(preservation_path, preservation_payload)

        output["merge_id_map_ref"] = artifact_ref(id_map_path, artifact_root)
        output["artifact_map_ref"] = artifact_ref(artifact_map_path, artifact_root)
        output["materialization_preservation_report_ref"] = artifact_ref(preservation_path, artifact_root)

    return owner_ok(
        owner_action="multi_source_merge_databases",
        capability="multi_source_merge_domain_service",
        target_identity=target_identity,
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "multi_source_merge_databases",
            "merge_run_id": str(selection.get("merge_run_id", "")),
            "target_database_path_hash": target_identity["target_database_path_hash"],
        },
    )


def _merge_mode_for_sources(payload: Mapping[str, Any], source_class: str) -> str:
    requested = str(payload.get("mode") or payload.get("merge_mode") or "additive").strip()
    if requested not in {"additive", "empty_semantic_only", "filled_sql_and_artifacts"}:
        raise ValueError("merge_mode must be additive, empty_semantic_only or filled_sql_and_artifacts.")
    derived = "empty_semantic_only" if source_class == "empty" else "filled_sql_and_artifacts"
    if requested != "additive" and requested != derived:
        raise ValueError(f"merge_mode_mismatch: {source_class} sources require {derived}.")
    return derived


def _load_collision_manifest(payload: Mapping[str, Any], manifest_root: Path) -> dict[str, Any]:
    inline_manifest = payload.get("collision_manifest")
    if (
        isinstance(inline_manifest, Mapping)
        and inline_manifest.get("schema_version") == "kernel.database_merge_collision_manifest.v1"
        and inline_manifest.get("manifest_fingerprint")
    ):
        return dict(inline_manifest)
    collision_ref = _mapping(payload, "collision_manifest_ref")
    artifact_path = str(collision_ref.get("artifact_path") or "").strip()
    path = validate_artifact_path_within_root(artifact_root_for_merge_manifest_root(manifest_root), artifact_path) if artifact_path else manifest_root / "merge_collision_manifest.json"
    return load_manifest(path)


def _write_artifact_stage_manifest(
    path: Path,
    *,
    selection: Mapping[str, Any],
    status: str,
    stage_report: Mapping[str, Any],
    sql_mutation_report: Mapping[str, Any] | None = None,
    artifact_copy_report: Mapping[str, Any] | None = None,
    cleanup_report: Mapping[str, Any] | None = None,
    error: str = "",
) -> None:
    payload = {
        "schema_version": "kernel.database_merge_artifact_stage.v1",
        "merge_run_id": str(selection.get("merge_run_id", "")),
        "created_at": utc_iso(),
        "status": status,
        "target_artifact_root": str(selection.get("target_artifact_root", "")),
        "target_database_path": str(selection.get("target_database_path", "")),
        "stage_report": dict(stage_report),
        "sql_mutation_report": dict(sql_mutation_report or {}),
        "artifact_copy_report": dict(artifact_copy_report or {}),
        "cleanup_report": dict(cleanup_report or {}),
        "error": error,
    }
    payload["manifest_fingerprint"] = manifest_fingerprint(payload)
    write_manifest(path, payload)


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _compact_artifact_copy_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "copied_artifact_count": int(report.get("copied_artifact_count") or 0),
    }


def _compact_artifact_stage_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "staged_artifact_count": int(report.get("staged_artifact_count") or 0),
    }
