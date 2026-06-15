from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity
from semantic_control_kernel.types.events import MirrorEvent
from semantic_control_kernel.types.rebuild import RebuildWorkflowExecution
from semantic_control_kernel.workflows.rebuild.final_notice_guidance import COMPLETION_ACTIONS, agent_guidance


def append_rebuild_final_notice(execution: RebuildWorkflowExecution) -> None:
    if _has_final_notice(execution):
        return
    blocked = execution.status == "blocked"
    focus = "workflow_blocked" if blocked else "workflow_completion"
    detail = _detail(execution, blocked=blocked)
    payload: dict[str, Any] = {
        "schema_version": MirrorEvent.SCHEMA_VERSION,
        "mirror_event_id": generate_id("mirror_event_id"),
        "mirror_source": "kernel",
        "is_kernel_auto_call": True,
        "event_type": MirrorEventType.BLOCKER.value if blocked else MirrorEventType.WORKFLOW_COMPLETED.value,
        "severity": MirrorSeverity.WARNING.value if blocked else MirrorSeverity.INFO.value,
        "user_visible_summary": _summary(execution, blocked=blocked),
        "current_state_summary": execution.final_state,
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
        "kernel_dialog_state": "not_required",
        "allowed_agent_tools": [] if blocked else list(COMPLETION_ACTIONS),
        "agent_explanation_guidance": agent_guidance(focus=focus, blocked=blocked),
        "technical_detail_ref": {
            "kind": f"database_rebuild_{focus}",
            focus: detail,
        },
    }
    event = MirrorEvent.from_dict(payload)
    _persist_mirror(execution, event)
    execution.mirror_events.append(event.to_dict())


def _has_final_notice(execution: RebuildWorkflowExecution) -> bool:
    for event in execution.mirror_events:
        detail = event.get("technical_detail_ref")
        if isinstance(detail, Mapping) and str(detail.get("kind", "")).startswith("database_rebuild_workflow_"):
            return True
    return False


def _detail(execution: RebuildWorkflowExecution, *, blocked: bool) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "workflow_family": "database_rebuild",
        "workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "rebuild_run_id": execution.rebuild_run_id,
        "artifact_root": execution.artifact_root,
        "target_database_path": execution.target_database_path,
        "loaded_release_identity": _loaded_release_identity(execution),
        "completed_step_ids": list(execution.completed_step_ids),
        "created_artifacts": _created_artifacts(execution),
        "kernel_persistence": _kernel_persistence(execution),
        "outcome": _outcome(execution, blocked=blocked),
        "workflow_explanation_context": _workflow_explanation_context(execution),
    }
    if blocked and execution.blocker is not None:
        detail["blocker"] = execution.blocker.to_dict()
    if not blocked:
        detail["next_step_options"] = [
            {
                "action": action,
                "surface": "permanent_agent_tool",
                "safety": "available_after_active_rebuilt_release",
            }
            for action in COMPLETION_ACTIONS
        ]
    return detail


def _loaded_release_identity(execution: RebuildWorkflowExecution) -> dict[str, Any]:
    loaded = execution.artifacts.get("loaded_release")
    if not isinstance(loaded, Mapping):
        return {}
    keys = (
        "loaded_release_path",
        "loaded_release_fingerprint",
        "loaded_semantic_release_id",
        "loaded_semantic_release_version",
        "runtime_locale",
    )
    return {key: loaded.get(key) for key in keys if loaded.get(key) not in (None, "")}


def _created_artifacts(execution: RebuildWorkflowExecution) -> dict[str, Any]:
    artifacts: dict[str, Any] = {
        "artifact_root": execution.artifact_root,
        "target_database_path": execution.target_database_path,
        "loaded_release_path": execution.artifacts.get("loaded_release_path"),
        "rebuild_manifest_path": execution.artifacts.get("rebuild_manifest_path"),
        "overwrite_receipt_id": execution.artifacts.get("overwrite_receipt_id"),
    }
    manifest = execution.artifacts.get("rebuild_manifest")
    if isinstance(manifest, Mapping):
        artifacts["rebuild_manifest_fingerprint"] = manifest.get("manifest_fingerprint")
        artifacts["record_count"] = manifest.get("record_count")
        artifacts["embedding_result"] = manifest.get("embedding_result")
        artifacts["activation_receipt_id"] = manifest.get("activation_receipt_id")
    return {key: value for key, value in artifacts.items() if value not in (None, "", {})}


def _kernel_persistence(execution: RebuildWorkflowExecution) -> dict[str, Any]:
    return {
        "semantic_release_loaded": "loading_semantic_release" in execution.completed_step_ids,
        "corpus_rebuilt": "running_rebuild" in execution.completed_step_ids,
        "embeddings_created_or_skipped": "creating_embeddings" in execution.completed_step_ids,
        "semantic_release_attached": "attaching_semantic_release" in execution.completed_step_ids,
        "semantic_release_active": execution.final_state == "semantic_release_active",
        "rebuild_manifest_written": bool(execution.artifacts.get("rebuild_manifest_path")),
        "rebuild_locks_released": all(
            not isinstance(lock, Mapping) or lock.get("status") != "active"
            for lock in execution.artifacts.get("locks", [])
        ),
    }


def _outcome(execution: RebuildWorkflowExecution, *, blocked: bool) -> dict[str, Any]:
    return {
        "rebuild_completed": not blocked and execution.status == "completed",
        "semantic_release_active": execution.final_state == "semantic_release_active",
        "database_ready_for_ingest": execution.final_state == "semantic_release_active",
        "overwrite_confirmed": bool(execution.artifacts.get("overwrite_receipt_id")),
    }


def _workflow_explanation_context(execution: RebuildWorkflowExecution) -> dict[str, Any]:
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
        "provenance_policy": "kernel_rebuild_state_and_owner_adapter_receipts_only",
    }


def _summary(execution: RebuildWorkflowExecution, *, blocked: bool) -> str:
    if blocked:
        blocker_summary = execution.blocker.user_visible_summary if execution.blocker else "Rebuild workflow is blocked."
        return f"{execution.workflow_tool} blocked at {execution.blocked_step_id or 'unknown_step'}: {blocker_summary}"
    suffix = (
        f" Artifact Tree: {execution.artifact_root}; database: {execution.target_database_path}."
        if execution.artifact_root and execution.target_database_path
        else ""
    )
    return f"Database rebuild is complete: one Corpus database was rebuilt from artifacts and activated.{suffix}"


def _persist_mirror(execution: RebuildWorkflowExecution, event: MirrorEvent) -> None:
    paths = StatePaths.from_state_root(Path(execution.state_root))
    paths.ensure_layout()
    MirrorEventStore(paths).append_mirror_event(event)
