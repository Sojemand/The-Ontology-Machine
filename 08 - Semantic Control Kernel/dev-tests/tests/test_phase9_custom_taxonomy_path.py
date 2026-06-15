from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.database_creation_interaction_resume import database_creation_interaction_resume_inputs
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_custom_taxonomy_path_builds_update_state_before_domain_call(tmp_path) -> None:
    target = target_for(tmp_path)
    llm = FakeLLMPort()
    semantic = FakeSemanticReleaseAdapter()
    samples = sample_refs_for(target)

    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic, llm_port=llm, taxonomy_samples=samples),
        workflow_run_id="wf_taxonomy",
    )

    assert execution.status == "completed"
    assert execution.artifacts["taxonomy_update_state"]["schema_version"] == "kernel.create_taxonomy_update_state.input.v1"
    analyze_call = [payload for name, payload in llm.calls if name == "analyze_samples"][0]
    assert analyze_call[0]["schema_version"] == "kernel.analyze_sample.input.v1"
    assert execution.operation_log.index("create_taxonomy_update_state") < execution.operation_log.index("create_custom_taxonomy")
    assert "create_custom_taxonomy" in semantic.calls


def test_custom_taxonomy_no_projections_stages_full_update_state(tmp_path) -> None:
    target = target_for(tmp_path)
    llm = FakeLLMPort()
    semantic = FakeSemanticReleaseAdapter()
    samples = sample_refs_for(target)

    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_no_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic, llm_port=llm, taxonomy_samples=samples),
        workflow_run_id="wf_custom_taxonomy_staged",
    )

    stage_payload = semantic.last_payloads["stage_taxonomy"][0]
    taxonomy_ref = execution.artifacts["taxonomy_ref"]

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_incomplete"
    assert stage_payload["update_state"]["schema_version"] == "kernel.create_taxonomy_update_state.input.v1"
    assert stage_payload["update_state"]["taxonomy_core"] == execution.artifacts["taxonomy_update_state"]["taxonomy_core"]
    assert execution.artifacts["staged_taxonomy_ref"]["source_analysis_refs"][0]["taxonomy_core"] == execution.artifacts["taxonomy_update_state"]["taxonomy_core"]
    assert taxonomy_ref["taxonomy_core"] == execution.artifacts["taxonomy_update_state"]["taxonomy_core"]
    assert {item["code"] for item in taxonomy_ref["field_codes"]} >= {"issuer", "other"}

    resume_inputs = database_creation_interaction_resume_inputs(
        workflow_run_id="wf_custom_taxonomy_staged",
        state_paths=StatePaths.from_state_root(tmp_path / "state"),
    )
    assert resume_inputs.artifacts["taxonomy_ref"]["taxonomy_core"] == execution.artifacts["taxonomy_update_state"]["taxonomy_core"]


def test_custom_taxonomy_path_rejects_missing_samples_without_mutation(tmp_path) -> None:
    semantic = FakeSemanticReleaseAdapter()
    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(tmp_path, target=target_for(tmp_path), semantic_adapter=semantic, llm_port=FakeLLMPort()),
        workflow_run_id="wf_taxonomy_missing_samples",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "input_missing"
    assert semantic.calls == []


def test_custom_taxonomy_path_rejects_missing_sample_file_without_llm_call(tmp_path) -> None:
    target = target_for(tmp_path)
    llm = FakeLLMPort()
    semantic = FakeSemanticReleaseAdapter()
    missing_sample = {"sample_id": "ghost", "path": str(Path(target.input_path) / "ghost.json")}

    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=llm,
            taxonomy_samples=[missing_sample],
        ),
        workflow_run_id="wf_taxonomy_missing_sample_file",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "input_missing"
    assert llm.calls == []
    assert semantic.calls == []


def test_custom_taxonomy_path_stops_on_final_llm_validation_failure(tmp_path) -> None:
    semantic = FakeSemanticReleaseAdapter()
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(fail_final="create_taxonomy_to_sample_analyses"),
            taxonomy_samples=sample_refs_for(target),
        ),
        workflow_run_id="wf_taxonomy_llm_fail",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "final_llm_validation_failure"
    assert "create_custom_taxonomy" not in semantic.calls
