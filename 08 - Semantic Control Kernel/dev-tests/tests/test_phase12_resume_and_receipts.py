from __future__ import annotations

from phase12_merge_entry_support import FakeMergeAdapter, runtime_for, seed_rebuild_release, source, target_root
from test_phase12_rebuild_workflow import rebuild_runtime

from semantic_control_kernel.workflows.merge.entry import database_merge_additive_only
from semantic_control_kernel.workflows.rebuild.entry import database_rebuild_from_artifacts


def test_merge_resume_state_records_selection_manifest_and_last_step(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_resume_success",
    )

    assert execution.resume_state["merge_run_id"] == execution.merge_run_id
    assert execution.resume_state["source_selection_fingerprint"] == execution.selection["selection_fingerprint"]
    assert execution.operation_receipts


def test_resume_at_reconciliation_keeps_collision_manifest_fingerprint(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_resume_reconcile",
    )

    assert execution.status == "blocked"
    assert execution.resume_state["collision_manifest_fingerprint"] == execution.artifacts["collision_manifest"]["manifest_fingerprint"]
    assert execution.blocker.recovery_state_class == "unresolved_merge_collision"


def test_resume_after_owner_call_records_adapter_receipts(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_resume_owner",
    )

    receipt_functions = [receipt["function_name"] for receipt in execution.operation_receipts]
    assert "merge_database_filled_additive" in receipt_functions
    assert "write_combined_database" not in receipt_functions
    assert execution.resume_state["id_map_fingerprint"] == execution.artifacts["id_map"]["map_fingerprint"]


def test_failed_merge_marks_lock_failed(tmp_path) -> None:
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=FakeMergeAdapter(semantic_collision=True)),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_lock_failed",
    )

    assert execution.artifacts["locks"][0]["status"] == "failed"


def test_successful_rebuild_releases_locks_and_records_manifest(tmp_path) -> None:
    from phase12_merge_entry_support import create_artifact_tree

    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="resume_rebuild",
        workflow_run_id="wf_rebuild_resume",
    )

    assert execution.status == "completed"
    assert all(lock["status"] == "released" for lock in execution.artifacts["locks"])
    assert execution.resume_state["rebuild_run_id"] == execution.rebuild_run_id


def test_target_identity_changed_blocker_for_stale_overwrite_receipt(tmp_path) -> None:
    from phase12_merge_entry_support import create_artifact_tree

    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    target = root / "Corpus" / "stale.db"
    target.write_text("old", encoding="utf-8")
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="stale.db",
        workflow_run_id="wf_stale_receipt",
        overwrite_receipt={
            "status": "confirmed",
            "artifact_root": str(root),
            "target_database_path": str(target),
            "loaded_release_fingerprint": "sha256:wrong",
            "workflow_run_id": "wf_stale_receipt",
        },
    )

    assert execution.status == "blocked"
    assert execution.blocker.recovery_state_class == "target_identity_changed"
