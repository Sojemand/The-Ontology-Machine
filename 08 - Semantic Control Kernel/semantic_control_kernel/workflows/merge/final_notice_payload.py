from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.merge import MergeWorkflowExecution


def _workflow_explanation_context(execution: MergeWorkflowExecution) -> dict[str, Any]:
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
        "provenance_policy": "kernel_merge_state_and_owner_adapter_receipts_only",
    }


def _created_artifacts(execution: MergeWorkflowExecution) -> dict[str, Any]:
    selection = execution.selection or {}
    artifacts: dict[str, Any] = {
        "target_artifact_root_path": selection.get("target_artifact_root"),
        "target_database_path": selection.get("target_database_path"),
    }
    for source_key, target_key in {
        "merge_selection_path": "merge_selection_path",
        "custom_release_path": "custom_release_path",
    }.items():
        value = execution.artifacts.get(source_key)
        if value:
            artifacts[target_key] = value
    manifest = execution.artifacts.get("collision_manifest")
    if isinstance(manifest, Mapping):
        artifacts["collision_manifest_fingerprint"] = manifest.get("manifest_fingerprint")
    id_map = execution.artifacts.get("id_map")
    if isinstance(id_map, Mapping):
        artifacts["merge_id_map_fingerprint"] = id_map.get("map_fingerprint")
    artifact_copy_report = execution.artifacts.get("artifact_copy_report")
    if isinstance(artifact_copy_report, Mapping):
        artifacts["copied_artifact_count"] = artifact_copy_report.get("copied_artifact_count")
    return {key: value for key, value in artifacts.items() if value not in (None, "", {})}


def _kernel_persistence(execution: MergeWorkflowExecution) -> dict[str, Any]:
    artifact_copy_report = execution.artifacts.get("artifact_copy_report")
    return {
        "merge_selection_written": bool(execution.artifacts.get("merge_selection_path")),
        "collision_manifest_written": "building_collision_manifest" in execution.completed_step_ids,
        "merge_id_map_written": bool(execution.artifacts.get("id_map")),
        "artifact_tree_files_copied": bool(artifact_copy_report.get("copied_artifact_count"))
        if isinstance(artifact_copy_report, Mapping) else False,
        "custom_release_written": bool(execution.artifacts.get("custom_release_path")),
        "semantic_release_attached": "attaching_semantic_release" in execution.completed_step_ids,
        "semantic_release_active": execution.final_state == "semantic_release_active",
        "merge_locks_released": all(
            not isinstance(lock, Mapping) or lock.get("status") != "active"
            for lock in execution.artifacts.get("locks", [])
        ),
    }


def _outcome(execution: MergeWorkflowExecution, *, route: str, blocked: bool) -> dict[str, Any]:
    return {
        "additive_merge_completed": not blocked and execution.status == "completed",
        "semantic_release_active": execution.final_state == "semantic_release_active",
        "database_ready_for_ingest": execution.final_state == "semantic_release_active",
        "empty_merge": route == "empty_databases_merge_path",
        "filled_merge": route == "filled_databases_merge_path",
        "source_database_count": _source_count(execution.selection or {}),
    }


def _source_count(selection: Mapping[str, Any]) -> int:
    sources = selection.get("source_databases")
    return len(sources) if isinstance(sources, list) else 0


def _source_summaries(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    sources = selection.get("source_databases")
    if not isinstance(sources, list):
        return []
    summaries: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        summaries.append({
            "source_database_id": source.get("source_database_id"),
            "source_database_path": source.get("source_database_path"),
            "source_state": source.get("source_state"),
            "source_semantic_release_id": source.get("source_semantic_release_id"),
            "source_semantic_release_version": source.get("source_semantic_release_version"),
        })
    return summaries
