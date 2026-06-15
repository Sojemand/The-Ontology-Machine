from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution
from semantic_control_kernel.validation.merge_validation import validate_materialization_refs_preserved
from semantic_control_kernel.workflows.merge.collision_manifest import reuse_existing_manifest
from semantic_control_kernel.workflows.merge.empty_merge import _finalize_release, _require_route, _target_identity, _write_selection
from semantic_control_kernel.workflows.merge.filled_merge_blockers import (
    id_map_invalid,
    invalid_owner_response,
    mark_locks_failed,
    release_locks,
)
from semantic_control_kernel.workflows.merge.final_notice import append_merge_final_notice
from semantic_control_kernel.workflows.merge.id_map import build_id_map
from semantic_control_kernel.workflows.merge.filled_merge_owner_artifacts import (
    artifact_ref_for_path,
    compact_artifact_copy_report,
    compact_id_map,
    id_map_mappings_from_owner,
)
from semantic_control_kernel.workflows.merge.receipts import (
    adapter_output,
    block_execution,
    blocker_from_adapter_result,
    complete_step,
    merge_run_dir,
    start_step,
    write_json,
)
from semantic_control_kernel.workflows.merge.reconciliation import reconcile_merged_database
from semantic_control_kernel.workflows.merge.semantic_merge import merge_taxonomy_and_projections_additive
from semantic_control_kernel.workflows.merge.sql_backfill import backfill_sql


def filled_databases_merge_path(
    *,
    runtime: object,
    selection: Mapping[str, Any],
    workflow_run_id: str | None = None,
    execution: MergeWorkflowExecution | None = None,
    reconciliation_receipt: Mapping[str, Any] | None = None,
) -> MergeWorkflowExecution:
    execution = execution or MergeWorkflowExecution(
        workflow_run_id=workflow_run_id or generate_id("workflow_run_id"),
        workflow_tool="filled_databases_merge_path",
        merge_run_id=str(selection["merge_run_id"]),
        state_root=getattr(runtime, "state_root", Path(".")),
        selection=dict(selection),
    )
    execution.selection = dict(selection)
    blocker = _require_route(selection, "filled")
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    _write_selection(execution)
    source_count = _source_count(selection)
    target_name = Path(str(selection["target_artifact_root"])).name or "target Artifact Tree"
    start_step(
        execution,
        "creating_target_artifact_tree",
        f"Creating the target Artifact Tree '{target_name}' for a {source_count}-source filled database merge.",
    )
    prepare = runtime.workspace_adapter.prepare_artifact_tree(
        {
            "merge_run_id": execution.merge_run_id,
            "selection": dict(selection),
            "target_identity": _target_identity(selection),
        }
    )
    blocker = blocker_from_adapter_result("creating_target_artifact_tree", prepare, function_name="create_standard_artifact_folder_tree")
    if blocker is not None:
        block_execution(execution, blocker)
        return execution
    complete_step(execution, step_id="creating_target_artifact_tree", function_name="create_standard_artifact_folder_tree", adapter_results=[prepare])

    start_step(
        execution,
        "creating_target_database",
        f"Creating the empty target corpus database before copying {source_count} source database(s).",
    )
    db_result = runtime.corpus_adapter.create_empty_database(
        {
            "database_path": selection["target_database_path"],
            "target_identity": _target_identity(selection),
        }
    )
    blocker = blocker_from_adapter_result("creating_target_database", db_result, function_name="create_empty_database")
    if blocker is not None:
        mark_locks_failed(execution)
        block_execution(execution, blocker)
        return execution
    complete_step(execution, step_id="creating_target_database", function_name="create_empty_database", adapter_results=[db_result])

    start_step(
        execution,
        "running_filled_merge",
        f"Copying SQL rows, originals, page images, evidence artifacts and provenance from {source_count} source database(s). This can take a long time on large corpora.",
    )
    merge_result, blocker = merge_database_filled_additive(runtime.merge_adapter, selection)
    if blocker is not None:
        mark_locks_failed(execution)
        block_execution(execution, blocker)
        return execution
    output = adapter_output(merge_result)
    artifact_copy_report = compact_artifact_copy_report(output)
    if artifact_copy_report:
        execution.artifacts["artifact_copy_report"] = artifact_copy_report
    try:
        id_map = build_id_map(
            merge_run_id=execution.merge_run_id,
            source_databases=list(selection["source_databases"]),
            target_database_path=str(selection["target_database_path"]),
            mappings=id_map_mappings_from_owner(selection, output),
        ).to_dict()
    except ValueError as exc:
        mark_locks_failed(execution)
        block_execution(execution, id_map_invalid(str(exc)), final_state="support_only_unrecoverable")
        return execution
    provenance_blocker = validate_materialization_refs_preserved(id_map)
    if provenance_blocker is not None:
        mark_locks_failed(execution)
        block_execution(execution, provenance_blocker, final_state="support_only_unrecoverable")
        return execution
    id_map_path = write_json(merge_run_dir(selection["target_artifact_root"], execution.merge_run_id) / "merge_id_map.json", id_map)
    id_map_ref = output.get("merge_id_map_ref") if isinstance(output.get("merge_id_map_ref"), Mapping) else artifact_ref_for_path(selection, id_map_path)
    execution.artifacts["id_map"] = compact_id_map(id_map)
    complete_step(
        execution,
        step_id="running_filled_merge",
        function_name="merge_database_filled_additive",
        output_refs=[{"merge_id_map_path": id_map_path, "map_fingerprint": id_map["map_fingerprint"]}],
        adapter_results=[merge_result],
    )

    start_step(
        execution,
        "building_collision_manifest",
        "Merging taxonomy/projection release metadata and building the Semantic Release collision manifest.",
    )
    semantic, blocker, semantic_result = merge_taxonomy_and_projections_additive(
        runtime.merge_adapter,
        selection=selection,
        merge_result=output,
    )
    if blocker is not None or semantic is None:
        mark_locks_failed(execution)
        block_execution(execution, blocker or invalid_owner_response("building_collision_manifest"))
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
        "Reconciling merge collisions and writing the selected reconciliation manifest.",
    )
    reconciled, blocker = reconcile_merged_database(runtime.merge_adapter, manifest, reconciliation_receipt=reconciliation_receipt)
    if blocker is not None or reconciled is None:
        mark_locks_failed(execution)
        block_execution(execution, blocker or invalid_owner_response("awaiting_reconciliation"), final_state="unresolved_merge_collision")
        return execution
    execution.artifacts["collision_manifest"] = reconciled
    write_json(merge_run_dir(selection["target_artifact_root"], execution.merge_run_id) / "merge_collision_manifest.json", reconciled)
    complete_step(execution, step_id="awaiting_reconciliation", function_name="reconcile_merged_database")

    if output.get("backfill_required"):
        start_step(
            execution,
            "backfill_sql",
            "Backfilling merge metadata that the owner marked recoverable after the filled database merge.",
        )
    backfill_result, blocker = backfill_sql(runtime.corpus_adapter, {"selection": dict(selection), "merge_id_map_ref": dict(id_map_ref), "backfill_required": bool(output.get("backfill_required"))})
    if blocker is not None:
        mark_locks_failed(execution)
        block_execution(execution, blocker)
        return execution
    if backfill_result is not None:
        complete_step(execution, step_id="backfill_sql", function_name="backfill_sql", adapter_results=[backfill_result])

    if not _finalize_release(runtime, execution, selection, semantic["semantic_merge_package"], id_map=compact_id_map(id_map)):
        return execution
    release_locks(execution)
    execution.status = "completed"
    execution.final_state = "semantic_release_active"
    complete_step(execution, step_id="completed", function_name="merge_finalization_receipt", final_state="semantic_release_active")
    append_merge_final_notice(execution)
    return execution


def merge_database_filled_additive(merge_adapter: object, selection: Mapping[str, Any]) -> tuple[object, MergeWorkflowBlocker | None]:
    result = merge_adapter.merge_filled_databases({"selection": dict(selection), "mode": "additive"})
    return result, blocker_from_adapter_result("running_filled_merge", result, function_name="merge_database_filled_additive")


def write_combined_database(
    merge_adapter: object,
    selection: Mapping[str, Any],
    *,
    id_map: Mapping[str, Any],
    collision_manifest: Mapping[str, Any],
) -> tuple[object, MergeWorkflowBlocker | None]:
    result = merge_adapter.write_combined_database(
        {
            "collision_manifest": dict(collision_manifest),
            "id_map": dict(id_map),
            "selection": dict(selection),
        }
    )
    return result, blocker_from_adapter_result("writing_combined_database", result, function_name="write_combined_database")


def _source_count(selection: Mapping[str, Any]) -> int:
    return len([item for item in selection.get("source_databases", []) if isinstance(item, Mapping)])
