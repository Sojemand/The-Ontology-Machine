from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.batches import PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import MirrorEvent


COMPLETION_ACTIONS: tuple[str, ...] = ("manual_pipeline_run", "kernel_status")


def append_final_notice(
    execution: PipelineRunExecution,
    *,
    target: PipelineRunTarget,
    reset_manifest: Mapping[str, Any],
    manifest_path: Path,
    owner_output: Mapping[str, Any],
) -> None:
    if _has_final_notice(execution):
        return
    payload = {
        "schema_version": MirrorEvent.SCHEMA_VERSION,
        "mirror_event_id": generate_id("mirror_event_id"),
        "mirror_source": "kernel",
        "is_kernel_auto_call": True,
        "event_type": MirrorEventType.WORKFLOW_COMPLETED.value,
        "severity": MirrorSeverity.INFO.value,
        "user_visible_summary": _summary(target, owner_output=owner_output),
        "current_state_summary": execution.final_state,
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "kernel_dialog_state": "not_required",
        "allowed_agent_tools": list(COMPLETION_ACTIONS),
        "agent_explanation_guidance": _agent_guidance(),
        "technical_detail_ref": {
            "kind": "database_reset_workflow_completion",
            "workflow_completion": _completion_detail(execution, target, reset_manifest, manifest_path, owner_output),
        },
    }
    event = MirrorEvent.from_dict(payload)
    state_paths = StatePaths.from_state_root(Path(execution.state_root))
    state_paths.ensure_layout()
    MirrorEventStore(state_paths).append_mirror_event(event)
    execution.mirror_events.append(event.to_dict())


def _completion_detail(
    execution: PipelineRunExecution,
    target: PipelineRunTarget,
    reset_manifest: Mapping[str, Any],
    manifest_path: Path,
    owner_output: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "workflow_family": "database_reset",
        "workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "target_database_path": target.database_path,
        "artifact_root": target.artifact_root_path,
        "database_reset_manifest_path": str(manifest_path),
        "semantic_release_preserved": True,
        "empty_state_proven": True,
        "physical_compaction_performed": bool(owner_output.get("physical_compaction_performed")),
        "physical_compaction": dict(owner_output.get("physical_compaction") or {}),
        "wal_sidecar_cleanup": dict(owner_output.get("wal_sidecar_cleanup") or {}),
        "cleared_table_counts": dict(owner_output.get("cleared_table_counts") or {}),
        "post_reset_counts": dict(owner_output.get("post_reset_counts") or {}),
        "preserved_release_ref": dict(reset_manifest.get("preserved_release_ref") or {}),
        "completed_step_ids": list(execution.completed_step_ids),
        "workflow_explanation_context": _workflow_explanation_context(execution),
    }


def _has_final_notice(execution: PipelineRunExecution) -> bool:
    for event in execution.mirror_events:
        detail = event.get("technical_detail_ref")
        if isinstance(detail, Mapping) and detail.get("kind") == "database_reset_workflow_completion":
            return True
    return False


def _summary(target: PipelineRunTarget, *, owner_output: Mapping[str, Any]) -> str:
    compaction = " Physical DB compaction was performed." if owner_output.get("physical_compaction_performed") else ""
    return (
        "Database reset is complete: materialized Corpus content was cleared, "
        f"the active Semantic Release was preserved, and the DB is empty. Corpus DB: {target.database_path}."
        f"{compaction}"
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
        "performed_this_run": [{"fact_id": step_id, "evidence": "completed_step_ids"} for step_id in execution.completed_step_ids],
        "provenance_policy": "kernel_reset_state_and_owner_adapter_receipts_only",
    }


def _agent_guidance() -> dict[str, Any]:
    return {
        "response_mode": "emit_direct_message",
        "technical_detail_focus_path": "technical_detail_ref.workflow_completion",
        "workflow_explanation_context_path": "technical_detail_ref.workflow_completion.workflow_explanation_context",
        "goal": "Explain that the Kernel database reset finished and name what was cleared and preserved.",
        "style": "brief_operational_summary_with_done_state",
        "must_include": [
            "workflow_completed",
            "final_state",
            "target_database_path",
            "semantic_release_preserved",
            "empty_state_proven",
        ],
        "next_step_instruction": {"state_that_work_is_finished": True, "include_created_artifact_paths": True},
        "do_not_claim": [
            "that source artifacts were deleted",
            "that the Semantic Release was removed",
            "that a Kernel dialog is still waiting for input",
            "that the workflow is still running",
        ],
    }
