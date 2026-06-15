from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.batch_policy import artifact_ref
from semantic_control_kernel.types.batches import PipelineRunExecution, PipelineRunTarget, SEMANTIC_RELEASE_ACTIVE
from semantic_control_kernel.workflows.pipeline_run.batch_manifest import (
    build_final_manifest_from_owner_output,
    manifest_ref,
    pending_manifest_ref,
    write_final_manifest,
)
from semantic_control_kernel.workflows.pipeline_run.correlation import (
    blocker_code_for_correlation_failure,
    correlate_pipeline_outputs,
    write_correlation_report,
)
from semantic_control_kernel.workflows.pipeline_run.final_notice import append_pipeline_run_final_notice
from semantic_control_kernel.workflows.pipeline_run.run_support import (
    _adapter_output,
    _adapter_ref,
    _block,
    _blocker_from_adapter_result,
    _complete,
    _owner_final_manifest,
    create_blocker,
)


def finalize_pipeline_run(
    *,
    runtime,
    target: PipelineRunTarget,
    execution: PipelineRunExecution,
    pending: Mapping[str, Any],
    owner_result: object,
    workflow_run_id: str,
    pipeline_batch_id: str,
) -> PipelineRunExecution:
    owner_output = _adapter_output(owner_result)
    final_manifest = _owner_final_manifest(owner_output) or build_final_manifest_from_owner_output(
        target=target,
        pending_manifest=pending,
        owner_output=owner_output,
    )
    report = correlate_pipeline_outputs(pending_manifest=pending, final_manifest=final_manifest, owner_output=owner_output)
    report_path = write_correlation_report(target.artifact_root_path, report)
    execution.artifacts["correlation_report"] = report
    execution.artifacts["correlation_report_path"] = str(report_path)
    _complete(execution, "correlating_outputs", "kernel.pipeline_run_correlation_report.v1", output_refs=[artifact_ref(report_path, target.artifact_root)])
    if not report["manifest_eligible"]:
        _block_correlation_failure(execution, report)
        return execution
    if not _finalize_owner_manifest(runtime, target, execution, pending, final_manifest, report, workflow_run_id, pipeline_batch_id):
        return execution
    execution.status = "completed"
    execution.final_state = SEMANTIC_RELEASE_ACTIVE
    _complete(execution, "completed", "pipeline_run", output_refs=[manifest_ref(target, final_manifest)])
    append_pipeline_run_final_notice(
        execution,
        target=target,
        final_manifest=final_manifest,
        final_manifest_path=Path(str(execution.artifacts["final_manifest_path"])),
        correlation_report_path=report_path,
    )
    return execution


def _finalize_owner_manifest(runtime, target: PipelineRunTarget, execution: PipelineRunExecution, pending: Mapping[str, Any], final_manifest: Mapping[str, Any], report: Mapping[str, Any], workflow_run_id: str, pipeline_batch_id: str) -> bool:
    finalize_result = runtime.batch_adapter.finalize_batch_manifest(
        {
            "workflow_run_id": workflow_run_id,
            "target_identity": target.target_identity,
            "pipeline_batch_id": pipeline_batch_id,
            "artifact_root": target.artifact_root_path,
            "pending_manifest_ref": pending_manifest_ref(target, pending),
            "orchestrator_run_ref": dict(final_manifest.get("owner_run_refs", {})),
            "corpus_load_refs": list(final_manifest.get("owner_run_refs", {}).get("corpus_load_receipt_refs", [])),
            "output_artifacts": dict(final_manifest.get("output_artifacts", {})),
            "materialized_records": list(final_manifest.get("materialized_records", [])),
            "record_counts": dict(final_manifest.get("record_counts", {})),
            "final_manifest": final_manifest,
            "correlation_report": report,
        }
    )
    blocker = _blocker_from_adapter_result("finalize_batch_manifest", finalize_result, before_owner_mutation=False)
    if blocker is not None:
        _block(execution, blocker)
        return False
    return _record_final_manifest(target, execution, final_manifest, finalize_result)


def _record_final_manifest(target: PipelineRunTarget, execution: PipelineRunExecution, final_manifest: Mapping[str, Any], finalize_result: object) -> bool:
    try:
        final_path = _ensure_final_manifest_written(target, final_manifest)
    except FileExistsError as exc:
        _block(
            execution,
            create_blocker(
                step_id="finalizing_manifest",
                function_or_route="pipeline_run",
                blocker_code="partial_pipeline_run",
                recovery_state_class="partial_pipeline_run",
                summary=str(exc),
            ),
        )
        return False
    execution.artifacts["final_manifest"] = final_manifest
    execution.artifacts["final_manifest_path"] = str(final_path)
    _complete(
        execution,
        "finalizing_manifest",
        "BatchReingestAdapter.finalize_batch_manifest",
        output_refs=[manifest_ref(target, final_manifest)],
        pipeline_adapter_receipts=[_adapter_ref(finalize_result)],
    )
    return True


def _block_correlation_failure(execution: PipelineRunExecution, report: Mapping[str, Any]) -> None:
    _block(
        execution,
        create_blocker(
            step_id="correlating_outputs",
            function_or_route="pipeline_run",
            blocker_code=blocker_code_for_correlation_failure(report),
            recovery_state_class="partial_pipeline_run",
            summary="Pipeline owner output could not be safely correlated into a final batch manifest.",
            diagnostics=report.get("mismatch_diagnostics", ()),
        ),
    )


def _ensure_final_manifest_written(target: PipelineRunTarget, final_manifest: Mapping[str, Any]) -> Path:
    path = Path(target.artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / str(final_manifest["pipeline_batch_id"]) / "pipeline_batch_manifest.json"
    if not path.exists():
        return write_final_manifest(target, final_manifest)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise FileExistsError("Final pipeline batch manifest exists but could not be verified.")
    if not isinstance(existing, Mapping):
        raise FileExistsError("Final pipeline batch manifest exists but is not a JSON object.")
    if existing.get("manifest_fingerprint") != final_manifest.get("manifest_fingerprint"):
        raise FileExistsError("Final pipeline batch manifest already exists with a different fingerprint.")
    return path
