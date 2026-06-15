from __future__ import annotations
from copy import deepcopy

from ..semantic_release.multi_source_merge_types import path_hash
from ..semantic_release.multi_source_merge_manifests import (
    artifact_ref,
    artifact_root_for_merge_manifest_root,
    load_manifest,
    manifest_fingerprint,
    merge_manifest_root,
    utc_iso,
    write_manifest,
)
from ..semantic_release.multi_source_merge_policy import build_collision_summary
from ..semantic_release.multi_source_merge_validation import validate_artifact_path_within_root, validate_merge_selection, validate_target_identity

from ..database_analysis import read_database_analysis_evidence
from ..pipeline_batches import (
    cleanup_pipeline_batch_materialization,
    extract_sample_files_for_reingest,
    inspect_latest_pipeline_batch,
    reingest_pipeline_batch,
    restore_pipeline_batch_originals,
)
from ..semantic_release.multi_source_merge_backfill import backfill_sql_from_merge_artifacts
from ..semantic_release.multi_source_merge_preflight import multi_source_merge_preflight
from ..semantic_release.multi_source_merge_workflow import multi_source_merge_databases
from ..standalone_artifacts.artifact_tree_contract import validate_artifact_tree
from .types import (
    BackfillSqlFromMergeArtifactsCommand,
    CleanupPipelineBatchMaterializationCommand,
    ExtractSampleFilesForReingestCommand,
    InspectLatestPipelineBatchCommand,
    MultiSourceMergeDatabasesCommand,
    MultiSourceMergePreflightCommand,
    ReadDatabaseAnalysisEvidenceCommand,
    ReingestPipelineBatchCommand,
    RestorePipelineBatchOriginalsCommand,
    ValidateArtifactTreeCommand,
    WriteMergeReconciliationManifestCommand,
)


def handle_validate_artifact_tree(command: ValidateArtifactTreeCommand, *, context):
    return validate_artifact_tree(command.payload)


def handle_read_database_analysis_evidence(command: ReadDatabaseAnalysisEvidenceCommand, *, context):
    return read_database_analysis_evidence(command.payload)


def handle_inspect_latest_pipeline_batch(command: InspectLatestPipelineBatchCommand, *, context):
    return inspect_latest_pipeline_batch(command.payload)


def handle_extract_sample_files_for_reingest(command: ExtractSampleFilesForReingestCommand, *, context):
    return extract_sample_files_for_reingest(command.payload)


def handle_restore_pipeline_batch_originals(command: RestorePipelineBatchOriginalsCommand, *, context):
    return restore_pipeline_batch_originals(command.payload)


def handle_cleanup_pipeline_batch_materialization(command: CleanupPipelineBatchMaterializationCommand, *, context):
    return cleanup_pipeline_batch_materialization(command.payload)


def handle_reingest_pipeline_batch(command: ReingestPipelineBatchCommand, *, context):
    return reingest_pipeline_batch(command.payload)


def handle_multi_source_merge_preflight(command: MultiSourceMergePreflightCommand, *, context):
    return multi_source_merge_preflight(command.payload)


def handle_multi_source_merge_databases(command: MultiSourceMergeDatabasesCommand, *, context):
    return multi_source_merge_databases(command.payload)


def handle_write_merge_reconciliation_manifest(command: WriteMergeReconciliationManifestCommand, *, context):
    payload = dict(command.payload)
    selection = payload.get("selection") if isinstance(payload.get("selection"), dict) else {}
    if selection:
        validate_merge_selection(selection)
    target_database_path = str(payload.get("target_database_path") or selection.get("target_database_path") or "")
    target_identity = {
        "merge_run_id": str(payload.get("merge_run_id") or selection.get("merge_run_id") or ""),
        "target_database_path_hash": path_hash(target_database_path) if target_database_path else "",
    }
    validate_target_identity(selection or {"merge_run_id": target_identity["merge_run_id"], "target_database_path": target_database_path, "source_databases": []}, payload.get("target_identity") if isinstance(payload.get("target_identity"), dict) else target_identity)
    manifest_root = merge_manifest_root(
        str(selection.get("target_artifact_root") or payload.get("target_artifact_root") or ""),
        target_identity["merge_run_id"],
    )
    artifact_root = artifact_root_for_merge_manifest_root(manifest_root)
    manifest = _load_collision_manifest(payload, manifest_root)
    collisions = [deepcopy(item) for item in manifest.get("collisions", []) if isinstance(item, dict)]
    selected_resolutions = [dict(item) for item in payload.get("selected_resolutions", []) if isinstance(item, dict)]
    selected_by_collision = {str(item.get("collision_id") or ""): item for item in selected_resolutions if item.get("collision_id")}
    if collisions:
        for collision in collisions:
            collision_id = str(collision.get("collision_id") or "")
            resolution = selected_by_collision.get(collision_id)
            if resolution is None and collision.get("resolution_status") in {"unresolved", "requires_user_choice"}:
                raise ValueError("unresolved_merge_collision: reconciliation requires a selected resolution for every blocking collision.")
            if resolution is not None:
                collision["selected_resolution"] = str(resolution.get("selected_resolution") or "")
                collision["resolution_status"] = "resolved"
        if any(item.get("resolution_status") in {"unresolved", "requires_user_choice"} for item in collisions):
            raise ValueError("unresolved_merge_collision: unresolved blocking collisions remain after reconciliation.")
    manifest["collisions"] = collisions
    manifest["updated_at"] = utc_iso()
    manifest["manifest_revision"] = int(manifest.get("manifest_revision", 1)) + 1
    manifest["resolution_summary"] = build_collision_summary(collisions)
    manifest["manifest_fingerprint"] = manifest_fingerprint(manifest)
    collision_manifest_path = manifest_root / "merge_collision_manifest.json"
    write_manifest(collision_manifest_path, manifest)
    return {
        "status": "ok",
        "output_refs": {
            "updated_collision_manifest_ref": artifact_ref(collision_manifest_path, artifact_root),
            "manifest_revision": int(manifest.get("manifest_revision", 1)),
            "resolution_summary": dict(manifest.get("resolution_summary", {})),
            "manifest_fingerprint": str(manifest.get("manifest_fingerprint", "")),
        },
        "target_identity_proof": {
            key: value
            for key, value in target_identity.items()
            if value
        },
        "receipt_fields": {"owner_module": "05 - Corpus Builder", "owner_action": "write_merge_reconciliation_manifest", "merge_run_id": str(payload.get("merge_run_id", ""))},
        "diagnostics": [],
        "detail": {
            "schema_version": "kernel.pipeline_owner_result.v1",
            "owner_module": "05 - Corpus Builder",
            "owner_action": "write_merge_reconciliation_manifest",
            "capability": "multi_source_merge_domain_service",
            "status": "ok",
            "target_identity": target_identity,
            "artifact_refs": {},
            "receipt_fields": {"owner_module": "05 - Corpus Builder", "owner_action": "write_merge_reconciliation_manifest", "merge_run_id": str(payload.get("merge_run_id", ""))},
            "diagnostics": [],
            "warnings": [],
        },
    }


def handle_backfill_sql_from_merge_artifacts(command: BackfillSqlFromMergeArtifactsCommand, *, context):
    return backfill_sql_from_merge_artifacts(command.payload)


def _load_collision_manifest(payload: dict[str, object], manifest_root) -> dict:
    inline_manifest = payload.get("collision_manifest")
    if (
        isinstance(inline_manifest, dict)
        and inline_manifest.get("schema_version") == "kernel.database_merge_collision_manifest.v1"
        and inline_manifest.get("manifest_fingerprint")
    ):
        return dict(inline_manifest)
    collision_ref = payload.get("collision_manifest_ref")
    if isinstance(collision_ref, dict) and collision_ref.get("artifact_path"):
        path = validate_artifact_path_within_root(artifact_root_for_merge_manifest_root(manifest_root), str(collision_ref["artifact_path"]))
        return load_manifest(path)
    return load_manifest(manifest_root / "merge_collision_manifest.json")
