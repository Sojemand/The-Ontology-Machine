from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.policy.batch_policy import build_materialization_ref, with_manifest_fingerprint
from semantic_control_kernel.types.batches import PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.batch_manifest import (
    build_final_manifest_from_owner_output,
    build_pending_batch_manifest,
)

from phase11_target_fakes import input_files


def owner_output(count: int = 2) -> dict[str, Any]:
    records = [
        {
            "document_id": f"doc_{index:03d}",
            "record_id": f"record_{index:03d}",
            "artifact_refs": [{"artifact_path": f"Documents/normalized/doc_{index:03d}.json"}],
            "embedding_ref": f"embedding_{index:03d}",
        }
        for index in range(1, count + 1)
    ]
    return {
        "owner_run_refs": {
            "orchestrator_run_id": "orch_run_001",
            "orchestrator_receipt_ref": "receipts/orchestrator.json",
            "corpus_load_receipt_refs": ["receipts/corpus_load.json"],
            "embedding_receipt_refs": [],
        },
        "materialized_records": records,
        "record_counts": {
            "documents": count,
            "normalized_records": count,
            "projected_records": count,
            "embeddings": count,
            "error_cases": 0,
        },
        "database_record_counts": {
            "documents": count,
            "normalized_records": count,
            "projected_records": count,
            "embeddings": count,
            "error_cases": 0,
        },
        "output_artifacts": {
            "raw_extracts": [],
            "structured": [],
            "normalized": [{"artifact_path": "Documents/normalized/doc_001.json"}],
            "validation": [],
            "page_images": [],
            "requests": [],
            "error_cases": [],
        },
    }


def owner_output_for_request(
    request_payload: Mapping[str, Any],
    *,
    output: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = deepcopy(dict(output or owner_output()))
    pipeline_batch_id = str(request_payload.get("pipeline_batch_id", ""))
    semantic_release = request_payload.get("semantic_release") if isinstance(request_payload.get("semantic_release"), Mapping) else {}
    projection = _first_projection(request_payload)
    records = payload.get("materialized_records")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            if isinstance(record.get("record_semantic_materialization_ref"), Mapping):
                continue
            record["record_semantic_materialization_ref"] = build_materialization_ref(
                pipeline_batch_id=pipeline_batch_id,
                document_id=str(record.get("document_id", "")),
                record_id=str(record.get("record_id", "")),
                semantic_release_id=str(semantic_release.get("semantic_release_id", "")),
                semantic_release_version=str(semantic_release.get("semantic_release_version", "")),
                release_fingerprint=str(semantic_release.get("release_fingerprint", "")),
                taxonomy_fingerprint=str(semantic_release.get("taxonomy_fingerprint", "")),
                projection_id=str(record.get("projection_id") or projection.get("projection_id", "")),
                projection_fingerprint=str(record.get("projection_fingerprint") or projection.get("projection_fingerprint", "")),
            )
    _add_input_file_dispositions(payload, request_payload, pipeline_batch_id)
    return payload


def final_manifest_for(
    target: PipelineRunTarget,
    *,
    batch_kind: str = "sample_ingest",
    workflow_run_id: str = "wf_manifest",
    output: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pending = build_pending_batch_manifest(
        target=target,
        workflow_run_id=workflow_run_id,
        pipeline_batch_id="pbt_20260506010101_1234abcd_1",
        batch_kind=batch_kind,
        input_files=[],
        created_by_workflow="pipeline_run",
    )
    pending["input_files"] = input_files()
    owner_payload = owner_output_for_request(
        {
            "pipeline_batch_id": pending["pipeline_batch_id"],
            "semantic_release": target.semantic_release_manifest_ref(),
            "active_projections": target.projection_manifest_refs(),
            "input_files": pending["input_files"],
        },
        output=output or owner_output(),
    )
    return build_final_manifest_from_owner_output(
        target=target,
        pending_manifest=pending,
        owner_output=owner_payload,
    )


def with_bad_final_manifest(base: Mapping[str, Any], mutator) -> dict[str, Any]:
    manifest = deepcopy(dict(base))
    mutator(manifest)
    return with_manifest_fingerprint(manifest)


def _first_projection(request_payload: Mapping[str, Any]) -> dict[str, Any]:
    active_projections = request_payload.get("active_projections")
    if isinstance(active_projections, list) and active_projections:
        first = active_projections[0]
        if isinstance(first, Mapping):
            return dict(first)
    return {}


def _add_input_file_dispositions(payload: dict[str, Any], request_payload: Mapping[str, Any], pipeline_batch_id: str) -> None:
    request_inputs = request_payload.get("input_files")
    if not isinstance(request_inputs, list) or "input_file_dispositions" in payload:
        return
    payload["input_file_dispositions"] = [
        {
            "input_file_id": str(item.get("input_file_id", "")),
            "pipeline_batch_id": pipeline_batch_id,
            "disposition": "materialized",
        }
        for item in request_inputs
        if isinstance(item, Mapping)
    ]
