from __future__ import annotations

from phase12_merge_entry_support import *  # noqa: F403

def test_filled_route_runs_after_preflight_and_selection(tmp_path) -> None:
    merge = FakeMergeAdapter()
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_filled",
    )

    assert execution.status == "completed"
    assert execution.selection["merge_route"] == "filled_databases_merge_path"
    assert "running_filled_merge" in execution.completed_step_ids
    assert "writing_combined_database" not in execution.completed_step_ids
    assert merge.request_payloads["merge_filled_databases"][0]["mode"] == "additive"
    reconcile_payload = merge.request_payloads["write_merge_reconciliation_manifest"][0]
    assert "reconciliation_receipt" not in reconcile_payload
    assert reconcile_payload["target_artifact_root"] == execution.selection["target_artifact_root"]
    assert reconcile_payload["target_database_path"] == execution.selection["target_database_path"]
    assert reconcile_payload["selected_resolutions"] == []

def test_filled_route_blocks_single_projection_merge_mode_before_target_mutation(tmp_path) -> None:
    merge = FakeMergeAdapter()
    runtime = runtime_for(tmp_path, merge_adapter=merge)
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        projection_merge_mode="merge_to_single_projection",
        workflow_run_id="wf_filled_single_projection_blocked",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "projection_merge_mode_not_supported"
    assert execution.blocked_step_id == "validating_projection_merge_mode"
    assert merge.calls == []
    assert runtime.workspace_adapter.calls == []

def test_mixed_empty_and_filled_selection_runs_filled_additive_route(tmp_path) -> None:
    runtime = runtime_for(tmp_path)
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[source(tmp_path, "a", state="empty"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_mixed",
    )

    assert execution.status == "completed"
    assert execution.selection["merge_route"] == "filled_databases_merge_path"
    assert runtime.workspace_adapter.calls == ["prepare_artifact_tree"]
    assert "create_empty_database" in runtime.corpus_adapter.calls
    assert execution.artifacts["id_map"]["record_count"] == 1

def test_no_target_mutation_when_multi_source_owner_missing(tmp_path) -> None:
    merge = FakeMergeAdapter(missing=True)
    runtime = runtime_for(tmp_path, merge_adapter=merge)
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_missing_owner",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert execution.blocker.recovery_state_class == "support_only_unrecoverable"
    assert runtime.workspace_adapter.calls == []

def test_selection_can_be_built_without_mutating_target(tmp_path) -> None:
    selection = build_database_merge_selection(
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        selected_by_interaction_id="interaction",
        merge_run_id="merge_selection",
    )

    assert selection.to_dict()["schema_version"] == "kernel.database_merge_selection.v1"
    assert not target_root(tmp_path).exists()
