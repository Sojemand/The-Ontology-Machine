from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, load_default_release_fixture, runtime_for, sample_refs_for, target_for
from phase9_custom_projection_support import NestedCustomReleaseAdapter, staged_taxonomy_ref, write_full_release_fixture
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_custom_projection_path_builds_authoring_view_before_llm_call(tmp_path) -> None:
    target = target_for(tmp_path)
    default_release = load_default_release_fixture()
    llm = FakeLLMPort()
    semantic = FakeSemanticReleaseAdapter()

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=llm,
            projection_samples=sample_refs_for(target, prefix="projection"),
            taxonomy_ref=default_release["taxonomy_ref"],
        ),
        workflow_run_id="wf_projection_active_taxonomy",
        initial_final_state="semantic_release_active",
    )

    proposal_call = [payload for name, payload in llm.calls if name == "create_projections_to_sample_analyses"][0]
    assert execution.status == "completed"
    assert execution.artifacts["projection_update_state"]["schema_version"] == "kernel.create_projections_update_state.input.v1"
    assert proposal_call["taxonomy_authoring_view"]["schema_version"] == "kernel.taxonomy_projection_authoring_view.v1"
    assert execution.artifacts["projection_update_state"]["taxonomy_ref"]["taxonomy_id"] == default_release["taxonomy_ref"]["taxonomy_id"]
    assert execution.artifacts["projection_update_state"]["taxonomy_ref"]["taxonomy_fingerprint"] == default_release["taxonomy_ref"]["taxonomy_fingerprint"]
    assert execution.operation_log.index("build_taxonomy_projection_authoring_view") < execution.operation_log.index("create_projections_to_sample_analyses")


def test_custom_projection_path_injects_full_release_taxonomy_into_authoring_view(tmp_path) -> None:
    target = target_for(tmp_path)
    release_path = write_full_release_fixture(target)
    llm = FakeLLMPort()

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            llm_port=llm,
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_projection_full_taxonomy",
        initial_final_state="semantic_release_active",
        initial_artifacts={
            "default_release_path": str(release_path),
            "taxonomy_ref": {
                "taxonomy_id": "taxonomy-default-fingerprint",
                "taxonomy_fingerprint": "taxonomy-default-fingerprint",
            },
        },
    )

    proposal_call = [payload for name, payload in llm.calls if name == "create_projections_to_sample_analyses"][0]
    view = proposal_call["taxonomy_authoring_view"]

    assert execution.status == "completed"
    assert set(view["allowed_codes"]["document_types"]) == {"invoice"}
    assert {"issuer", "amount_due", "other"}.issubset(set(view["allowed_codes"]["field_codes"]))
    assert [slot["slot"] for slot in view["promotion_slots"]] == ["counterparty"]
    assert view["promotion_slots"][0]["scope"] == "document"
    assert "Payment request" in view["term_summaries"]["invoice"]
    assert "invoice" in execution.artifacts["taxonomy_ref"]["allowed_codes"]


def test_custom_projection_path_validates_before_staging_or_release_creation(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter()

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_projection_staged_taxonomy",
        initial_final_state="semantic_release_incomplete",
        initial_artifacts={"staged_taxonomy_ref": staged_taxonomy_ref()},
        include_optional_steps=True,
    )

    assert execution.status == "completed"
    assert semantic.calls.index("validate_projections_against_taxonomy") < semantic.calls.index("stage_projections")
    assert semantic.calls.index("validate_projections_against_taxonomy") < semantic.calls.index("create_custom_semantic_release")
    release_payload = semantic.last_payloads["create_custom_semantic_release"][0]
    assert release_payload["semantic_release_folder"] == target.semantic_release_path
    assert execution.final_state == "semantic_release_active"


def test_custom_projection_path_unwraps_nested_custom_release_ref_before_write(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = NestedCustomReleaseAdapter()

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(),
            projection_samples=sample_refs_for(target, prefix="projection"),
            taxonomy_ref=load_default_release_fixture()["taxonomy_ref"],
        ),
        workflow_run_id="wf_projection_nested_release_ref",
        initial_final_state="semantic_release_incomplete",
        initial_artifacts={
            "default_release_path": str(Path(target.semantic_release_path) / "releases" / "default.release.v1"),
            "staged_taxonomy_ref": staged_taxonomy_ref(),
        },
        include_optional_steps=True,
    )

    write_payload = semantic.last_payloads["write_semantic_release"][0]
    assert execution.status == "completed"
    assert execution.artifacts["custom_release_ref"]["release_id"] == "custom.release.nested"
    assert write_payload["release_ref"]["release_id"] == "custom.release.nested"
    assert write_payload["base_release_path"]
    assert write_payload["projection_update_state"]["schema_version"] == "kernel.create_projections_update_state.input.v1"


def test_projection_validation_failure_blocks_before_staging(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter(invalid_projection_validation=True)

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(),
            projection_samples=sample_refs_for(target, prefix="projection"),
            taxonomy_ref=load_default_release_fixture()["taxonomy_ref"],
        ),
        workflow_run_id="wf_projection_invalid",
        initial_final_state="semantic_release_active",
        include_optional_steps=True,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "projection_taxonomy_invalid"
    assert "stage_projections" not in semantic.calls
