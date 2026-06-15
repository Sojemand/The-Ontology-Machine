from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.policy.batch_policy import (
    pending_batch_manifest_path,
    pipeline_batch_manifest_path,
    record_counts_from_materialized_records,
    with_manifest_fingerprint,
)
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunTarget


JsonObject = dict[str, Any]


def build_pending_batch_manifest(
    *,
    target: PipelineRunTarget,
    workflow_run_id: str,
    pipeline_batch_id: str,
    batch_kind: str,
    input_files: Sequence[PipelineInputFile],
    created_by_workflow: str,
) -> JsonObject:
    return {
        "schema_version": "kernel.pipeline_pending_batch_manifest.v1",
        "pipeline_batch_id": pipeline_batch_id,
        "workflow_run_id": workflow_run_id,
        "created_at": utc_iso(),
        "pending_status": "prepared",
        "created_by_workflow": created_by_workflow,
        "batch_kind": batch_kind,
        "active_database": target.active_database_manifest_ref(),
        "artifact_root": target.artifact_root_manifest_ref(),
        "semantic_release": target.semantic_release_manifest_ref(),
        "active_projections": target.projection_manifest_refs(),
        "input_files": [item.to_manifest_entry() for item in input_files],
    }


def build_final_manifest_from_owner_output(
    *,
    target: PipelineRunTarget,
    pending_manifest: Mapping[str, Any],
    owner_output: Mapping[str, Any],
) -> JsonObject:
    records = _materialized_records(owner_output)
    record_counts = _record_counts(owner_output, records)
    output_artifacts = _output_artifacts(owner_output)
    owner_refs = _owner_run_refs(owner_output)
    manifest = {
        "schema_version": "kernel.pipeline_batch_manifest.v1",
        "pipeline_batch_id": pending_manifest["pipeline_batch_id"],
        "workflow_run_id": pending_manifest["workflow_run_id"],
        "created_at": pending_manifest["created_at"],
        "finalized_at": utc_iso(),
        "batch_kind": pending_manifest["batch_kind"],
        "batch_status": "finalized",
        "active_database": deepcopy(pending_manifest["active_database"]),
        "artifact_root": deepcopy(pending_manifest["artifact_root"]),
        "semantic_release": deepcopy(pending_manifest["semantic_release"]),
        "active_projections": deepcopy(pending_manifest["active_projections"]),
        "input_files": deepcopy(pending_manifest["input_files"]),
        "owner_run_refs": owner_refs,
        "output_artifacts": output_artifacts,
        "materialized_records": records,
        "record_counts": record_counts,
        "cleanup_eligibility": _cleanup_eligibility(pending_manifest),
        "manifest_fingerprint": "",
    }
    for key in ("sample_selection_ref", "reingest_source_ref", "support_bundle_ref"):
        if key in owner_output:
            manifest[key] = deepcopy(owner_output[key])
    return with_manifest_fingerprint(manifest)


def write_pending_manifest(target: PipelineRunTarget, manifest: Mapping[str, Any]) -> Path:
    return _write_json(pending_batch_manifest_path(target.artifact_root_path, str(manifest["pipeline_batch_id"])), manifest)


def write_final_manifest(target: PipelineRunTarget, manifest: Mapping[str, Any]) -> Path:
    path = pipeline_batch_manifest_path(target.artifact_root_path, str(manifest["pipeline_batch_id"]))
    if path.exists():
        raise FileExistsError("Final pipeline batch manifests are immutable and must not be overwritten.")
    return _write_json(path, manifest)


def pending_manifest_ref(target: PipelineRunTarget, manifest: Mapping[str, Any]) -> JsonObject:
    path = pending_batch_manifest_path(target.artifact_root_path, str(manifest["pipeline_batch_id"]))
    return {
        "pipeline_batch_id": str(manifest["pipeline_batch_id"]),
        "manifest_path": str(path),
        "artifact_path": artifact_relpath(path, target.artifact_root),
    }


def manifest_ref(target: PipelineRunTarget, manifest: Mapping[str, Any]) -> JsonObject:
    path = pipeline_batch_manifest_path(target.artifact_root_path, str(manifest["pipeline_batch_id"]))
    return {
        "pipeline_batch_id": str(manifest["pipeline_batch_id"]),
        "manifest_path": str(path),
        "manifest_fingerprint": str(manifest.get("manifest_fingerprint", "")),
    }


def _materialized_records(
    owner_output: Mapping[str, Any],
) -> list[JsonObject]:
    owner_records = owner_output.get("materialized_records")
    if isinstance(owner_records, list):
        return [deepcopy(record) for record in owner_records if isinstance(record, Mapping)]
    return []


def _record_counts(owner_output: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> JsonObject:
    value = owner_output.get("record_counts")
    if isinstance(value, Mapping):
        return {
            "documents": int(value.get("documents", 0)),
            "normalized_records": int(value.get("normalized_records", 0)),
            "projected_records": int(value.get("projected_records", 0)),
            "embeddings": int(value.get("embeddings", 0)),
            "error_cases": int(value.get("error_cases", 0)),
        }
    return record_counts_from_materialized_records(records)


def _output_artifacts(owner_output: Mapping[str, Any]) -> JsonObject:
    value = owner_output.get("output_artifacts")
    keys = ("raw_extracts", "structured", "normalized", "validation", "page_images", "requests", "error_cases")
    if isinstance(value, Mapping):
        return {key: list(value.get(key, [])) if isinstance(value.get(key, []), list) else [] for key in keys}
    return {key: [] for key in keys}


def _owner_run_refs(owner_output: Mapping[str, Any]) -> JsonObject:
    value = owner_output.get("owner_run_refs")
    if isinstance(value, Mapping):
        return {
            "orchestrator_run_id": str(value.get("orchestrator_run_id", "")),
            "orchestrator_receipt_ref": str(value.get("orchestrator_receipt_ref", "")),
            "corpus_load_receipt_refs": list(value.get("corpus_load_receipt_refs", [])) if isinstance(value.get("corpus_load_receipt_refs", []), list) else [],
            "embedding_receipt_refs": list(value.get("embedding_receipt_refs", [])) if isinstance(value.get("embedding_receipt_refs", []), list) else [],
        }
    orchestrator_run_id = str(owner_output.get("orchestrator_run_id", ""))
    orchestrator_receipt_ref = str(owner_output.get("orchestrator_receipt_ref", ""))
    return {
        "orchestrator_run_id": orchestrator_run_id,
        "orchestrator_receipt_ref": orchestrator_receipt_ref,
        "corpus_load_receipt_refs": [],
        "embedding_receipt_refs": [],
    }


def _cleanup_eligibility(pending_manifest: Mapping[str, Any]) -> JsonObject:
    batch_kind = pending_manifest.get("batch_kind")
    targetable = batch_kind in {"sample_ingest", "reingest_selected_samples", "workflow_continuation_ingest"}
    return {
        "is_cleanup_targetable": targetable,
        "cleanup_scope": "selected_batch" if targetable else "manual_batch_not_cleanup_target",
        "requires_confirmation": True,
        "non_deletable_refs": [],
        "reason_if_not_targetable": None if targetable else "manual pipeline batches are not sample cleanup targets",
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    atomic_write_json(path, dict(payload))
    return path


def artifact_relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
