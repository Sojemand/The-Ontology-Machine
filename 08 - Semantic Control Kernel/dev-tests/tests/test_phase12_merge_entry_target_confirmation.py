from __future__ import annotations

from phase12_merge_entry_support import *  # noqa: F403

def test_existing_non_empty_merge_target_requires_confirmation_before_preflight(tmp_path) -> None:
    target = target_root(tmp_path)
    create_artifact_tree(target)
    (target / "Documents" / "logs" / "existing.txt").write_text("existing", encoding="utf-8")
    merge = FakeMergeAdapter()
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target,
        workflow_run_id="wf_existing_target_no_receipt",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "confirmation_missing"
    assert merge.calls == []

def test_previous_kernel_merge_log_residue_does_not_require_target_confirmation(tmp_path) -> None:
    target = target_root(tmp_path)
    stale_run_dir = target / "Documents" / "logs" / "merge_runs" / "mrg_stale"
    stale_run_dir.mkdir(parents=True)
    (stale_run_dir / "merge_selection.json").write_text("{}", encoding="utf-8")
    (stale_run_dir / "merge_collision_manifest.json").write_text("{}", encoding="utf-8")
    merge = FakeMergeAdapter()

    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target,
        workflow_run_id="wf_existing_target_only_merge_logs",
    )

    assert execution.status == "completed"
    assert "multi_source_merge_preflight" in merge.calls

def test_existing_non_empty_merge_target_confirmation_scope_allows_preflight(tmp_path) -> None:
    target = target_root(tmp_path)
    create_artifact_tree(target)
    (target / "Documents" / "logs" / "existing.txt").write_text("existing", encoding="utf-8")
    selected = [source(tmp_path, "a"), source(tmp_path, "b")]
    selection = build_database_merge_selection(
        selected_sources=selected,
        target_artifact_root=target,
        selected_by_interaction_id="interaction",
        merge_run_id="merge_existing_target_confirmed",
    ).to_dict()

    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path),
        selected_sources=selected,
        target_artifact_root=target,
        workflow_run_id="wf_existing_target_confirmed",
        merge_run_id="merge_existing_target_confirmed",
        target_confirmation_receipt=merge_target_confirmation(selection),
    )

    assert execution.status == "completed"
