from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.batch_policy import correlation_report_path, relative_artifact_ref_is_safe
from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.validation.batch_validation import BatchValidationError, validate_pipeline_batch_manifest


def correlate_pipeline_outputs(
    *,
    pending_manifest: Mapping[str, Any],
    final_manifest: Mapping[str, Any],
    owner_output: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    diagnostics.extend(_input_disposition_diagnostics(pending_manifest=pending_manifest, owner_output=owner_output))
    diagnostics.extend(_owner_evidence_diagnostics(pending_manifest=pending_manifest, owner_output=owner_output))
    try:
        validate_pipeline_batch_manifest(final_manifest)
    except BatchValidationError as exc:
        diagnostics.append({"code": "manifest_validation_failed", "message": str(exc)})
    except Exception as exc:
        diagnostics.append({"code": "manifest_validation_failed", "message": str(exc)})

    expected_batch = pending_manifest.get("pipeline_batch_id")
    if final_manifest.get("pipeline_batch_id") != expected_batch:
        diagnostics.append({"code": "pipeline_batch_id_mismatch"})

    expected_release = pending_manifest.get("semantic_release", {}).get("release_fingerprint")
    if final_manifest.get("semantic_release", {}).get("release_fingerprint") != expected_release:
        diagnostics.append({"code": "release_fingerprint_mismatch"})

    owner_counts = owner_output.get("database_record_counts")
    manifest_counts = final_manifest.get("record_counts", {})
    if isinstance(owner_counts, Mapping):
        for key in ("documents", "normalized_records", "projected_records", "embeddings", "error_cases"):
            if int(owner_counts.get(key, manifest_counts.get(key, 0))) != int(manifest_counts.get(key, 0)):
                diagnostics.append({"code": "record_count_mismatch", "field": key})

    artifact_root = str(final_manifest.get("artifact_root", {}).get("artifact_root_path", ""))
    for group, refs in final_manifest.get("output_artifacts", {}).items():
        if isinstance(refs, list):
            for ref in refs:
                path = str(ref.get("artifact_path") if isinstance(ref, Mapping) else ref)
                if not relative_artifact_ref_is_safe(path, artifact_root):
                    diagnostics.append({"code": "output_outside_artifact_tree", "group": group, "artifact_path": path})

    materialized_records = final_manifest.get("materialized_records", [])
    if isinstance(materialized_records, list):
        for record in materialized_records:
            if not isinstance(record, Mapping) or not isinstance(record.get("record_semantic_materialization_ref"), Mapping):
                diagnostics.append({"code": "materialization_provenance_missing"})
                break

    status = "passed" if not diagnostics else "failed"
    return {
        "schema_version": "kernel.pipeline_run_correlation_report.v1",
        "workflow_run_id": pending_manifest.get("workflow_run_id", ""),
        "pipeline_batch_id": expected_batch,
        "correlation_status": status,
        "manifest_eligible": status == "passed",
        "owner_output_refs": dict(owner_output.get("output_refs", {})) if isinstance(owner_output.get("output_refs"), Mapping) else {},
        "mismatch_diagnostics": diagnostics,
    }


def _input_disposition_diagnostics(
    *,
    pending_manifest: Mapping[str, Any],
    owner_output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    input_files = pending_manifest.get("input_files")
    if not isinstance(input_files, list) or not input_files:
        return []
    dispositions = owner_output.get("input_file_dispositions")
    if not isinstance(dispositions, list):
        return [{"code": "input_file_disposition_missing"}]
    by_input_id = {
        str(item.get("input_file_id")): item
        for item in dispositions
        if isinstance(item, Mapping) and item.get("input_file_id")
    }
    expected_batch = pending_manifest.get("pipeline_batch_id")
    diagnostics: list[dict[str, Any]] = []
    for input_file in input_files:
        if not isinstance(input_file, Mapping):
            diagnostics.append({"code": "input_file_disposition_missing"})
            continue
        input_file_id = str(input_file.get("input_file_id", ""))
        disposition = by_input_id.get(input_file_id)
        if not isinstance(disposition, Mapping):
            diagnostics.append({"code": "input_file_disposition_missing", "input_file_id": input_file_id})
            continue
        if disposition.get("pipeline_batch_id") != expected_batch:
            diagnostics.append({"code": "input_file_disposition_batch_mismatch", "input_file_id": input_file_id})
        if disposition.get("disposition") not in {"materialized", "error_case", "skipped_with_receipt"}:
            diagnostics.append({"code": "input_file_disposition_invalid", "input_file_id": input_file_id})
    return diagnostics


def write_correlation_report(artifact_root_path: str | Path, report: Mapping[str, Any]) -> Path:
    path = correlation_report_path(artifact_root_path, str(report["pipeline_batch_id"]))
    atomic_write_json(path, dict(report))
    return path


def blocker_code_for_correlation_failure(report: Mapping[str, Any]) -> str:
    codes = {
        str(item.get("code", ""))
        for item in report.get("mismatch_diagnostics", [])
        if isinstance(item, Mapping)
    }
    if "materialization_provenance_missing" in codes:
        return "materialization_provenance_missing"
    if "record_count_mismatch" in codes:
        return "partial_pipeline_run"
    if "owner_record_counts_missing" in codes:
        return "partial_pipeline_run"
    if "owner_run_evidence_missing" in codes:
        return "partial_pipeline_run"
    if "input_file_disposition_missing" in codes:
        return "partial_pipeline_run"
    if "input_file_disposition_batch_mismatch" in codes:
        return "partial_pipeline_run"
    if "input_file_disposition_invalid" in codes:
        return "partial_pipeline_run"
    if "release_fingerprint_mismatch" in codes:
        return "partial_pipeline_run"
    if "output_outside_artifact_tree" in codes:
        return "partial_pipeline_run"
    return "partial_pipeline_run"


def _owner_evidence_diagnostics(
    *,
    pending_manifest: Mapping[str, Any],
    owner_output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if isinstance(owner_output.get("final_manifest"), Mapping):
        return []
    diagnostics: list[dict[str, Any]] = []
    owner_records = owner_output.get("materialized_records")
    if (not isinstance(owner_records, list) or not owner_records) and not _all_inputs_accounted_as_error_cases(owner_output):
        diagnostics.append({"code": "materialization_provenance_missing"})
    if not isinstance(owner_output.get("record_counts"), Mapping) and not isinstance(owner_output.get("database_record_counts"), Mapping):
        diagnostics.append({"code": "owner_record_counts_missing"})
    owner_run_refs = owner_output.get("owner_run_refs")
    has_owner_run_refs = (
        isinstance(owner_run_refs, Mapping)
        and bool(owner_run_refs.get("orchestrator_run_id"))
        and bool(owner_run_refs.get("orchestrator_receipt_ref"))
    )
    has_flat_owner_run_refs = bool(owner_output.get("orchestrator_run_id")) and bool(owner_output.get("orchestrator_receipt_ref"))
    if not has_owner_run_refs and not has_flat_owner_run_refs:
        diagnostics.append(
            {
                "code": "owner_run_evidence_missing",
                "pipeline_batch_id": pending_manifest.get("pipeline_batch_id", ""),
            }
        )
    return diagnostics


def _all_inputs_accounted_as_error_cases(owner_output: Mapping[str, Any]) -> bool:
    dispositions = owner_output.get("input_file_dispositions")
    if not isinstance(dispositions, list) or not dispositions:
        return False
    if not all(isinstance(item, Mapping) and item.get("disposition") == "error_case" for item in dispositions):
        return False
    counts = owner_output.get("record_counts")
    if not isinstance(counts, Mapping):
        counts = owner_output.get("database_record_counts")
    if not isinstance(counts, Mapping):
        return False
    return int(counts.get("error_cases") or 0) >= len(dispositions)
