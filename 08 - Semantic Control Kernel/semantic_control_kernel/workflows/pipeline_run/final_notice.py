from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.batches import PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import MirrorEvent


COMPLETION_ACTIONS: tuple[str, ...] = (
    "manual_pipeline_run",
    "reset_database",
    "database_rebuild_from_artifacts",
    "kernel_status",
)


def append_pipeline_run_final_notice(
    execution: PipelineRunExecution,
    *,
    target: PipelineRunTarget,
    final_manifest: Mapping[str, Any],
    final_manifest_path: str | Path,
    correlation_report_path: str | Path,
) -> None:
    if _has_final_notice(execution):
        return
    counts = dict(final_manifest.get("record_counts") or {})
    detail = {
        "workflow_family": "manual_pipeline_run",
        "workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "target_database_path": target.database_path,
        "artifact_root": target.artifact_root_path,
        "input_file_count": len(final_manifest.get("input_files", [])) if isinstance(final_manifest.get("input_files"), list) else 0,
        "record_counts": counts,
        "pipeline_batch_id": str(final_manifest.get("pipeline_batch_id") or ""),
        "pipeline_batch_manifest_path": str(final_manifest_path),
        "manifest_fingerprint": str(final_manifest.get("manifest_fingerprint") or ""),
        "correlation_report_path": str(correlation_report_path),
        "owner_run_refs": dict(final_manifest.get("owner_run_refs") or {}),
        "output_artifacts": dict(final_manifest.get("output_artifacts") or {}),
        "completed_step_ids": list(execution.completed_step_ids),
        "workflow_explanation_context": _workflow_explanation_context(execution),
    }
    payload = {
        "schema_version": MirrorEvent.SCHEMA_VERSION,
        "mirror_event_id": generate_id("mirror_event_id"),
        "mirror_source": "kernel",
        "is_kernel_auto_call": True,
        "event_type": MirrorEventType.WORKFLOW_COMPLETED.value,
        "severity": MirrorSeverity.INFO.value,
        "user_visible_summary": _summary(target, counts=counts),
        "current_state_summary": execution.final_state,
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "kernel_dialog_state": "not_required",
        "allowed_agent_tools": list(COMPLETION_ACTIONS),
        "agent_explanation_guidance": _agent_guidance(),
        "technical_detail_ref": {
            "kind": "manual_pipeline_run_workflow_completion",
            "workflow_completion": detail,
        },
    }
    event = MirrorEvent.from_dict(payload)
    paths = StatePaths.from_state_root(Path(execution.state_root))
    paths.ensure_layout()
    MirrorEventStore(paths).append_mirror_event(event)
    execution.mirror_events.append(event.to_dict())


def _has_final_notice(execution: PipelineRunExecution) -> bool:
    for event in execution.mirror_events:
        detail = event.get("technical_detail_ref")
        if isinstance(detail, Mapping) and detail.get("kind") == "manual_pipeline_run_workflow_completion":
            return True
    return False


def _summary(target: PipelineRunTarget, *, counts: Mapping[str, Any]) -> str:
    documents = int(counts.get("documents") or 0)
    errors = int(counts.get("error_cases") or 0)
    review = int(counts.get("needs_review") or 0) if "needs_review" in counts else 0
    review_text = f", {review} review" if review else ""
    error_text = f", {errors} Error Case(s)" if errors else ", no Error Cases"
    return (
        f"Manual pipeline run is complete: {documents} document(s) materialized{review_text}{error_text}. "
        f"Corpus DB: {target.database_path}."
    )


def _workflow_explanation_context(execution: PipelineRunExecution) -> dict[str, Any]:
    return {
        "schema_version": "kernel.workflow_explanation_context.v1",
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "current_state_summary": execution.final_state,
        "completed_step_ids_total": list(execution.completed_step_ids),
        "completed_step_ids_at_run_start": [],
        "completed_step_ids_this_run": list(execution.completed_step_ids),
        "already_available": [],
        "performed_this_run": [
            {"fact_id": step_id, "evidence": "completed_step_ids"}
            for step_id in execution.completed_step_ids
        ],
        "provenance_policy": "kernel_batch_manifest_and_owner_adapter_receipts_only",
    }


def _agent_guidance() -> dict[str, Any]:
    return {
        "response_mode": "explain_now",
        "technical_detail_focus_path": "technical_detail_ref.workflow_completion",
        "workflow_explanation_context_path": "technical_detail_ref.workflow_completion.workflow_explanation_context",
        "goal": "Explain that the manual ingestion finished and name successful materialization and Error Case counts.",
        "style": "brief_operational_summary_with_done_state",
        "must_include": [
            "workflow_completed",
            "final_state",
            "target_database_path",
            "record_counts",
            "pipeline_batch_manifest_path",
        ],
        "next_step_instruction": {"state_that_work_is_finished": True, "include_created_artifact_paths": True},
        "do_not_claim": [
            "that failed Error Cases were ingested",
            "that source artifacts were deleted",
            "that the workflow is still running",
            "that a Kernel dialog is still waiting for input",
        ],
    }
