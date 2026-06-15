from __future__ import annotations

from phase12_merge_entry_support import FakeMergeAdapter, runtime_for, source, target_root

from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.merge.entry import database_merge_additive_only


def test_filled_merge_fills_artifacts_merges_sql_writes_id_map_and_activates(tmp_path) -> None:
    merge = FakeMergeAdapter()
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_filled_happy",
    )

    assert execution.status == "completed"
    assert merge.calls.count("merge_filled_databases") == 1
    assert "fill_artifact_tree" not in merge.calls
    assert "id_map" in execution.artifacts
    assert (target_root(tmp_path) / "Documents" / "logs" / "merge_runs" / execution.merge_run_id / "merge_id_map.json").exists()
    assert "write_combined_database" not in merge.calls


def test_filled_merge_persists_live_progress_before_long_owner_copy(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_filled_progress",
    )

    stored = [
        event.to_dict()
        for event in ProgressEventStore(StatePaths.from_state_root(tmp_path / "state")).list_progress_events(execution.workflow_run_id)
    ]
    running_copy = [
        event
        for event in stored
        if event["step_id"] == "running_filled_merge" and event["status"] == "step_started"
    ]

    assert running_copy
    assert "Copying SQL rows" in running_copy[0]["user_visible_summary"]
    assert running_copy[0]["step_label"] == "Copying source databases and artifacts"


def test_filled_merge_final_notice_exposes_id_map_context(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_filled_notice",
    )

    final_event = execution.mirror_events[-1]
    completion = final_event["technical_detail_ref"]["workflow_completion"]
    assert final_event["agent_explanation_guidance"]["response_mode"] == "explain_now"
    assert completion["merge_route"] == "filled_databases_merge_path"
    assert completion["kernel_persistence"]["merge_id_map_written"] is True
    assert completion["kernel_persistence"]["artifact_tree_files_copied"] is True
    assert completion["outcome"]["filled_merge"] is True
    assert "merge_id_map_fingerprint" in completion["created_artifacts"]
    assert completion["created_artifacts"]["copied_artifact_count"] == 2


def test_filled_merge_runs_optional_backfill_when_owner_marks_recoverable(tmp_path) -> None:
    merge = FakeMergeAdapter(backfill_required=True)
    runtime = runtime_for(tmp_path, merge_adapter=merge)
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_backfill",
    )

    assert execution.status == "completed"
    assert "backfill_sql" in runtime.corpus_adapter.calls


def test_filled_merge_blocks_when_materialization_refs_cannot_be_preserved(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(missing_materialization=True)),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_missing_refs",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "materialization_provenance_missing"


def test_user_choice_collision_blocks_until_reconciliation_receipt(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_filled_collision",
    )

    assert execution.status == "blocked"
    assert execution.blocker.recovery_state_class == "unresolved_merge_collision"
