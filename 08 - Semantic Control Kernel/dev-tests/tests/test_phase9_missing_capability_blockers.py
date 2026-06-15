from __future__ import annotations

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, FakeWorkspaceAdapter, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_missing_workspace_capability_blocks_before_database_creation(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target, workspace_adapter=FakeWorkspaceAdapter(missing_prepare=True)),
        workflow_run_id="wf_missing_workspace",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert "dc_create_empty_database" not in execution.completed_step_ids


def test_missing_semantic_release_domain_service_preserves_llm_artifacts(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter(missing_methods=["create_custom_taxonomy"])
    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(),
            taxonomy_samples=sample_refs_for(target),
        ),
        workflow_run_id="wf_missing_semantic_domain",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert execution.artifacts["taxonomy_update_state"]["schema_version"] == "kernel.create_taxonomy_update_state.input.v1"


def test_unavailable_llm_function_port_blocks_custom_paths(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(tmp_path, target=target, taxonomy_samples=sample_refs_for(target)),
        workflow_run_id="wf_no_llm",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert execution.blocked_step_id == "tax_analyze_samples"
