"""Owner evidence helpers for Kernel-driven pipeline runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..workspace_domain.policy import path_hash
from .pipeline_owner_records import (
    artifact_ref,
    collect_record_artifacts,
    document_rows_for_input,
    empty_output_artifacts,
    input_disposition,
    materialization_ref,
    record_counts,
)


def pipeline_owner_output_refs(*, engine: Any, ui_state: Any, summary: Any, request_payload: dict[str, Any]) -> dict[str, Any]:
    pipeline_batch_id = str(request_payload.get("pipeline_batch_id") or "")
    input_files = list(request_payload.get("input_files") or [])
    semantic_release = mapping_field(request_payload, "semantic_release")
    active_projections = request_payload.get("active_projections")
    projection = active_projections[0] if isinstance(active_projections, list) and active_projections and isinstance(active_projections[0], dict) else {}
    db_path = Path(str(getattr(ui_state, "selected_corpus_db_path", "") or request_payload.get("database_path") or ""))
    artifact_root = Path(str(getattr(ui_state, "artifact_folder", "") or ""))
    dispositions: list[dict[str, Any]] = []
    materialized_records: list[dict[str, Any]] = []
    output_artifacts = empty_output_artifacts()
    tracked_hashes = set(getattr(summary, "tracked_hashes", ()) or ())
    input_hashes = {str(item.get("content_hash") or "") for item in input_files if isinstance(item, dict)}
    relevant_hashes = tracked_hashes | {value for value in input_hashes if value}
    for item in input_files:
        if isinstance(item, dict):
            _collect_input_evidence(
                engine,
                item,
                pipeline_batch_id,
                db_path,
                semantic_release,
                projection,
                artifact_root,
                dispositions,
                materialized_records,
                output_artifacts,
            )
    for content_hash in relevant_hashes - input_hashes:
        record = engine._state.documents.get(content_hash)
        if record is not None:
            collect_record_artifacts(output_artifacts, record, artifact_root=artifact_root)
    proof = run_target_identity_proof(ui_state, request_payload, mapping_field(request_payload, "target_identity"))
    counts = record_counts(
        db_path=db_path,
        materialized_records=materialized_records,
        error_cases=sum(1 for item in dispositions if item.get("disposition") == "error_case"),
    )
    return {
        "pipeline_batch_id": pipeline_batch_id,
        "database_path": str(db_path),
        "database_path_hash": proof.get("database_path_hash", ""),
        "artifact_root_path": str(artifact_root),
        "artifact_root_path_hash": proof.get("artifact_root_path_hash", ""),
        "owner_run_refs": _owner_run_refs(summary, artifact_root),
        "input_file_dispositions": dispositions,
        "output_artifacts": output_artifacts,
        "materialized_records": materialized_records,
        "record_counts": counts,
        "database_record_counts": dict(counts),
    }


def run_target_identity_proof(ui_state: Any, request_payload: dict[str, Any], target_identity: dict[str, Any]) -> dict[str, Any]:
    database_path = str(getattr(ui_state, "selected_corpus_db_path", "") or "")
    artifact_root = str(getattr(ui_state, "artifact_folder", "") or "")
    pipeline_batch_id = str(request_payload.get("pipeline_batch_id") or "")
    return {
        "database_path": database_path,
        "database_path_hash": _identity_or_hash(target_identity, "database_path_hash", database_path),
        "artifact_root_path": artifact_root,
        "artifact_root_path_hash": _identity_or_hash(target_identity, "artifact_root_path_hash", artifact_root),
        "pipeline_batch_id": pipeline_batch_id,
    }


def mapping_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _collect_input_evidence(
    engine: Any,
    item: dict[str, Any],
    pipeline_batch_id: str,
    db_path: Path,
    semantic_release: dict[str, Any],
    projection: dict[str, Any],
    artifact_root: Path,
    dispositions: list[dict[str, Any]],
    materialized_records: list[dict[str, Any]],
    output_artifacts: dict[str, list[dict[str, str]]],
) -> None:
    content_hash = str(item.get("content_hash") or "")
    record = engine._state.documents.get(content_hash)
    db_rows = document_rows_for_input(db_path, item, record)
    disposition = input_disposition(record, db_rows)
    dispositions.append(
        {
            "input_file_id": str(item.get("input_file_id") or ""),
            "pipeline_batch_id": pipeline_batch_id,
            "disposition": disposition,
        }
    )
    if record is not None:
        collect_record_artifacts(output_artifacts, record, artifact_root=artifact_root)
    if disposition != "materialized" or not db_rows:
        return
    existing_ids = {str(item.get("document_id") or "") for item in materialized_records}
    for db_row in db_rows:
        db_document_id = str(db_row.get("document_id") or "")
        if not db_document_id or db_document_id in existing_ids:
            continue
        existing_ids.add(db_document_id)
        materialized_records.append(
            {
                "document_id": db_document_id,
                "record_id": db_document_id,
                "record_semantic_materialization_ref": materialization_ref(
                    pipeline_batch_id=pipeline_batch_id,
                    document_id=db_document_id,
                    record_id=db_document_id,
                    semantic_release=semantic_release,
                    projection=projection,
                ),
            }
        )


def _owner_run_refs(summary: Any, artifact_root: Path) -> dict[str, Any]:
    return {
        "orchestrator_run_id": str(getattr(summary, "run_id", "") or ""),
        "orchestrator_receipt_ref": artifact_ref(getattr(summary, "run_log_path", ""), artifact_root),
        "corpus_load_receipt_refs": [],
        "embedding_receipt_refs": [],
    }


def _identity_or_hash(target_identity: dict[str, Any], key: str, path_value: str) -> str:
    value = target_identity.get(key)
    if isinstance(value, str) and value:
        return value
    return path_hash(path_value) if path_value else ""
