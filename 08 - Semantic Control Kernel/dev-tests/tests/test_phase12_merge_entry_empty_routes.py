from __future__ import annotations

from phase12_merge_entry_support import *  # noqa: F403

def test_source_count_validation_blocks_before_owner_preflight(tmp_path) -> None:
    merge = FakeMergeAdapter()
    runtime = runtime_for(tmp_path, merge_adapter=merge)
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[source(tmp_path, "a")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_count",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "input_missing"
    assert merge.calls == []

def test_empty_route_runs_after_preflight_and_selection(tmp_path) -> None:
    merge = FakeMergeAdapter()
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_empty",
    )

    assert execution.status == "completed"
    assert execution.selection["merge_route"] == "empty_databases_merge_path"
    assert "running_empty_merge" in execution.completed_step_ids
    assert execution.artifacts["locks"][0]["status"] == "released"
    assert merge.request_payloads["merge_empty_databases"][0]["mode"] == "additive"
    semantic_sources = merge.request_payloads["merge_semantic_release_candidates"][0]["source_releases"]
    assert semantic_sources[0]["taxonomy_ref"]["taxonomy_id"] == "release.a.taxonomy"
    assert semantic_sources[0]["projection_refs"][0]["projection_id"] == "release.a.projection"
    assert merge.request_payloads["merge_semantic_release_candidates"][0]["projection_merge_mode"] == "preserve_source_projections"

def test_empty_route_allows_single_projection_merge_mode(tmp_path) -> None:
    merge = FakeMergeAdapter()
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, merge_adapter=merge),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        projection_merge_mode="merge_to_single_projection",
        workflow_run_id="wf_empty_single_projection",
    )

    assert execution.status == "completed"
    assert execution.selection["projection_merge_mode"] == "merge_to_single_projection"
    assert merge.request_payloads["merge_semantic_release_candidates"][0]["projection_merge_mode"] == "merge_to_single_projection"

def test_merge_finalization_unwraps_nested_release_ref_from_create_result(tmp_path) -> None:
    semantic_adapter = FakeSemanticReleaseAdapter(nested_create_output=True)
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, semantic_adapter=semantic_adapter),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_nested_create_release_ref",
    )

    assert execution.status == "completed"
    assert execution.artifacts["custom_release_ref"]["release_id"] == "merged.release"
    assert execution.artifacts["custom_release_ref"]["release_version"] == "1.0.0"
    assert execution.artifacts["custom_release_ref"]["release_fingerprint"] == "sha256:merged"

def test_merge_activation_uses_materialized_release_fingerprint_from_write(tmp_path) -> None:
    semantic_adapter = FakeSemanticReleaseAdapter(materialized_fingerprint="sha256:written_bundle")
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, semantic_adapter=semantic_adapter),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_materialized_release_fingerprint",
    )

    assert execution.status == "completed"
    assert execution.artifacts["custom_release_ref"]["release_fingerprint"] == "sha256:written_bundle"
    assert execution.artifacts["custom_release_path"].endswith("release.json")
    assert semantic_adapter.request_payloads["preflight_semantic_release_activation"][0]["release_ref"]["release_fingerprint"] == "sha256:written_bundle"
    assert semantic_adapter.request_payloads["activate_semantic_release"][0]["release_ref"]["release_fingerprint"] == "sha256:written_bundle"

def test_merge_attach_uses_kernel_pointer_without_pre_activation_owner_load(tmp_path) -> None:
    semantic_adapter = FakeSemanticReleaseAdapter(fail_load=True)
    execution = database_merge_additive_only(
        runtime=runtime_for(tmp_path, semantic_adapter=semantic_adapter),
        selected_sources=[source(tmp_path, "a"), source(tmp_path, "b")],
        target_artifact_root=target_root(tmp_path),
        workflow_run_id="wf_merge_attach_without_load",
    )

    assert execution.status == "completed"
    assert "load_semantic_release" not in semantic_adapter.calls
    assert "attaching_semantic_release" in execution.completed_step_ids
    assert semantic_adapter.calls.index("write_semantic_release") < semantic_adapter.calls.index("preflight_semantic_release_activation")
