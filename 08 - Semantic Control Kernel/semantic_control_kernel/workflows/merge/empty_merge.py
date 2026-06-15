from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution
from semantic_control_kernel.workflows.merge.collision_manifest import activation_is_blocked, reuse_existing_manifest
from semantic_control_kernel.workflows.merge.empty_merge_release import _finalize_release
from semantic_control_kernel.workflows.merge.empty_merge_support import (
    _fail_locks,
    _invalid,
    _release_locks,
    _require_route,
    _target_identity,
    _unresolved,
    _write_selection,
)
from semantic_control_kernel.workflows.merge.final_notice import append_merge_final_notice
from semantic_control_kernel.workflows.merge.receipts import (
    adapter_output,
    block_execution,
    blocker_from_adapter_result,
    complete_step,
    merge_run_dir,
    start_step,
    write_json,
)
from semantic_control_kernel.workflows.merge.reconciliation import reconcile_merged_semantic_release
from semantic_control_kernel.workflows.merge.semantic_merge import merge_taxonomy_and_projections_additive


def empty_databases_merge_path(
    *,
    runtime: object,
    selection: Mapping[str, Any],
    workflow_run_id: str | None = None,
    execution: MergeWorkflowExecution | None = None,
    reconciliation_receipt: Mapping[str, Any] | None = None,
) -> MergeWorkflowExecution:
    execution = execution or MergeWorkflowExecution(
        workflow_run_id=workflow_run_id or generate_id("workflow_run_id"),
        workflow_tool="empty_databases_merge_path",
        merge_run_id=str(selection["merge_run_id"]),
        state_root=getattr(runtime, "state_root", Path(".")),
        selection=dict(selection),
    )
    execution.selection = dict(selection)
    blocker = _require_route(selection, "empty")
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    _write_selection(execution)
    source_count = _source_count(selection)
    target_name = Path(str(selection["target_artifact_root"])).name or "target Artifact Tree"
    start_step(
        execution,
        "creating_target_artifact_tree",
        f"Creating the target Artifact Tree '{target_name}' for a {source_count}-source empty database merge.",
    )
    prepare_result = runtime.workspace_adapter.prepare_artifact_tree(
        {"merge_run_id": execution.merge_run_id, "selection": dict(selection), "target_identity": _target_identity(selection)}
    )
    blocker = blocker_from_adapter_result("creating_target_artifact_tree", prepare_result, function_name="create_standard_artifact_folder_tree")
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    complete_step(execution, step_id="creating_target_artifact_tree", function_name="create_standard_artifact_folder_tree", adapter_results=[prepare_result])

    start_step(
        execution,
        "creating_target_database",
        "Creating the empty target corpus database for the merged release.",
    )
    db_result = runtime.corpus_adapter.create_empty_database({"database_path": selection["target_database_path"], "target_identity": _target_identity(selection)})
    blocker = blocker_from_adapter_result("creating_target_database", db_result, function_name="create_empty_database")
    if blocker is not None:
        _fail_locks(execution)
        block_execution(execution, blocker)
        return execution
    complete_step(execution, step_id="creating_target_database", function_name="create_empty_database", adapter_results=[db_result])

    start_step(
        execution,
        "running_empty_merge",
        f"Merging empty database release state from {source_count} source database(s).",
    )
    merge_result, blocker = merge_database_empty(runtime.merge_adapter, selection)
    if blocker is not None:
        _fail_locks(execution)
        block_execution(execution, blocker)
        return execution
    complete_step(execution, step_id="running_empty_merge", function_name="merge_database_empty", adapter_results=[merge_result])

    start_step(
        execution,
        "building_collision_manifest",
        "Merging taxonomy/projection release metadata and building the Semantic Release collision manifest.",
    )
    semantic, blocker, semantic_result = merge_taxonomy_and_projections_additive(runtime.merge_adapter, selection=selection, merge_result=adapter_output(merge_result))
    if blocker is not None or semantic is None:
        _fail_locks(execution)
        block_execution(execution, blocker or _invalid("building_collision_manifest"))
        return execution
    manifest_path = merge_run_dir(selection["target_artifact_root"], execution.merge_run_id) / "merge_collision_manifest.json"
    manifest = reuse_existing_manifest(manifest_path, semantic["collision_manifest"])
    manifest_path = write_json(manifest_path, manifest)
    execution.artifacts["collision_manifest"] = manifest
    complete_step(
        execution,
        step_id="building_collision_manifest",
        function_name="merge_taxonomy_and_projections_additive",
        output_refs=[{"merge_collision_manifest_path": manifest_path, "manifest_fingerprint": manifest["manifest_fingerprint"]}],
        adapter_results=[semantic_result],
    )

    start_step(
        execution,
        "awaiting_reconciliation",
        "Reconciling Semantic Release collisions before activation.",
    )
    reconciled, blocker = reconcile_merged_semantic_release(runtime.merge_adapter, manifest, reconciliation_receipt=reconciliation_receipt)
    if blocker is not None or reconciled is None:
        _fail_locks(execution)
        block_execution(execution, blocker or _invalid("awaiting_reconciliation"), final_state="unresolved_merge_collision")
        return execution
    execution.artifacts["collision_manifest"] = reconciled
    write_json(merge_run_dir(selection["target_artifact_root"], execution.merge_run_id) / "merge_collision_manifest.json", reconciled)
    complete_step(execution, step_id="awaiting_reconciliation", function_name="reconcile_merged_semantic_release")
    if activation_is_blocked(reconciled):
        _fail_locks(execution)
        block_execution(execution, _unresolved("awaiting_reconciliation"), final_state="unresolved_merge_collision")
        return execution

    if not _finalize_release(runtime, execution, selection, semantic["semantic_merge_package"], id_map=None):
        return execution
    _release_locks(execution)
    execution.status = "completed"
    execution.final_state = "semantic_release_active"
    complete_step(execution, step_id="completed", function_name="merge_finalization_receipt", final_state="semantic_release_active")
    append_merge_final_notice(execution)
    return execution


def merge_database_empty(merge_adapter: object, selection: Mapping[str, Any]) -> tuple[object, MergeWorkflowBlocker | None]:
    result = merge_adapter.merge_empty_databases({"selection": dict(selection), "mode": "additive"})
    return result, blocker_from_adapter_result("running_empty_merge", result, function_name="merge_database_empty")


def _source_count(selection: Mapping[str, Any]) -> int:
    return len([item for item in selection.get("source_databases", []) if isinstance(item, Mapping)])


__all__ = [
    "_finalize_release",
    "_require_route",
    "_target_identity",
    "_write_selection",
    "empty_databases_merge_path",
    "merge_database_empty",
]
