from __future__ import annotations

from phase12_merge_entry_support import FakeMergeAdapter, merge_resolution, reconciliation_receipt, runtime_for, source, target_root

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_workflow_results import result_from_execution
from semantic_control_kernel.workflows.merge.entry import database_merge_additive_only


def test_empty_merge_creates_target_db_manifest_reconciles_and_activates(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_happy",
    )

    assert execution.status == "completed"
    assert (target_root(tmp_path) / "Corpus" / "corpus.db").exists()
    assert (target_root(tmp_path) / "Documents" / "logs" / "merge_runs" / execution.merge_run_id / "merge_collision_manifest.json").exists()
    assert (target_root(tmp_path) / "Semantic Release" / "releases" / "merged.release" / "release.json").is_file()
    assert execution.operation_log.index("merge_taxonomy_and_projections_additive") < execution.operation_log.index("attach_custom_semantic_release_to_database")
    assert execution.final_state == "semantic_release_active"
    attach_state = AttachStateStore(StatePaths.from_state_root(tmp_path / "state")).get_attach_state_for_database({"database_path": execution.selection["target_database_path"]})
    assert attach_state is not None
    assert attach_state.to_dict()["release_id"] == "merged.release"


def test_empty_merge_final_notice_exposes_explain_now_completion_context(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_notice",
    )

    final_event = execution.mirror_events[-1]
    assert final_event["event_type"] == "workflow_completed"
    assert final_event["agent_explanation_guidance"]["response_mode"] == "explain_now"
    assert final_event["agent_explanation_guidance"]["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    completion = final_event["technical_detail_ref"]["workflow_completion"]
    assert completion["workflow_family"] == "database_merge"
    assert completion["merge_route"] == "empty_databases_merge_path"
    assert completion["source_database_count"] == 2
    assert completion["outcome"]["database_ready_for_ingest"] is True
    assert completion["created_artifacts"]["target_artifact_root_path"] == str(target_root(tmp_path).resolve(strict=False))
    assert completion["created_artifacts"]["target_database_path"].endswith("Corpus\\corpus.db")
    result = result_from_execution(
        "database_merge_additive_only",
        execution.to_dict(),
        state_paths=StatePaths.from_state_root(tmp_path / "state"),
    ).to_dict()
    assert result["mirror_event"]["mirror_event_id"] == final_event["mirror_event_id"]
    stored = MirrorEventStore(StatePaths.from_state_root(tmp_path / "state")).get_mirror_event(final_event["mirror_event_id"])
    assert stored.to_dict()["technical_detail_ref"]["workflow_completion"]["merge_run_id"] == execution.merge_run_id


def test_empty_merge_missing_owner_blocks_before_target_mutation(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(missing=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_missing",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert not target_root(tmp_path).exists()


def test_empty_merge_requires_reconciliation_receipt_for_semantic_collision(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_collision",
    )

    assert execution.status == "blocked"
    assert execution.blocker.recovery_state_class == "unresolved_merge_collision"


def test_empty_merge_reconciliation_receipt_allows_activation(tmp_path) -> None:
    first = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_reconciled",
    )
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        merge_run_id=first.merge_run_id,
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_reconciled",
        reconciliation_receipt=reconciliation_receipt(
            manifest=first.artifacts["collision_manifest"],
            selected_resolutions=[merge_resolution("col_semantic_001", "rename_source_b")],
            workflow_run_id="wf_empty_reconciled",
        ),
    )

    assert execution.status == "completed"
    assert execution.artifacts["collision_manifest"]["resolution_summary"]["requires_user_choice"] == 0


def test_empty_merge_rejects_stale_reconciliation_receipt(tmp_path) -> None:
    first = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_stale_receipt",
    )
    stale_receipt = reconciliation_receipt(
        manifest=first.artifacts["collision_manifest"],
        selected_resolutions=[merge_resolution("col_semantic_001", "rename_source_b")],
        workflow_run_id="wf_empty_stale_receipt",
    )
    stale_receipt["manifest_revision_before"] = 999
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        merge_run_id=first.merge_run_id,
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty_stale_receipt",
        reconciliation_receipt=stale_receipt,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "merge_reconciliation_receipt_invalid"


def test_owner_cannot_mark_user_choice_collision_resolved_without_kernel_receipt(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(forged_resolved_semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_owner_forged_collision",
    )

    collision = execution.artifacts["collision_manifest"]["collisions"][0]
    assert execution.status == "blocked"
    assert execution.blocker.recovery_state_class == "unresolved_merge_collision"
    assert collision["resolution_status"] == "requires_user_choice"
    assert collision["resolution_owner"] == "kernel_dialog"
    assert collision["blocks_activation"] is True


def test_resume_reuses_persisted_import_local_source_ids_for_reconciliation(tmp_path) -> None:
    selected = [source(tmp_path, "a", durable=False), source(tmp_path, "b", durable=False)]
    first = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=selected,
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_import_local_resume",
        merge_run_id="merge_import_local_resume",
    )

    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=selected,
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_import_local_resume",
        merge_run_id="merge_import_local_resume",
        reconciliation_receipt=reconciliation_receipt(
            manifest=first.artifacts["collision_manifest"],
            selected_resolutions=[merge_resolution("col_semantic_001", "rename_source_b")],
            workflow_run_id="wf_import_local_resume",
        ),
    )

    assert execution.status == "completed"
    assert execution.selection["source_databases"][0]["source_database_id"] == first.selection["source_databases"][0]["source_database_id"]
