from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, runtime_for, sample_refs_for, target_for
from phase9_custom_projection_support import MinimalTaxonomyIdentityAdapter
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_empty_database_custom_taxonomy_custom_projection_route_reaches_final_notice(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter()

    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_custom_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(),
            taxonomy_samples=sample_refs_for(target, prefix="taxonomy"),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_custom_taxonomy_custom_projection",
    )

    release_payload = semantic.last_payloads["create_custom_semantic_release"][0]
    staged_taxonomy = release_payload["staged_taxonomy_ref"]["component_identity"]
    staged_projection = release_payload["staged_projection_ref"]["component_identity"]

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_active"
    assert [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"]
    assert "amount_due" in staged_taxonomy["allowed_codes"]
    assert "amount_due" in staged_projection["included_taxonomy_codes"]
    assert semantic.calls.index("stage_projections") < semantic.calls.index("create_custom_semantic_release")
    assert semantic.calls.index("create_custom_semantic_release") < semantic.calls.index("write_semantic_release")
    assert semantic.calls.index("write_semantic_release") < semantic.calls.index("load_semantic_release")
    assert semantic.calls[-1] == "activate_semantic_release"
    llm_step_ids = [event["step_id"] for event in execution.progress_events if event["event_type"] == "llm_step"]
    assert "llm_taxonomy_user_report_samples" in llm_step_ids
    assert "llm_projection_user_report_samples" in llm_step_ids
    assert "llm_user_report_samples" not in llm_step_ids


def test_creation_route_writes_analysis_artifacts_under_semantic_release_folder(tmp_path) -> None:
    target = target_for(tmp_path)
    llm = FakeLLMPort()

    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_custom_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=FakeSemanticReleaseAdapter(),
            llm_port=llm,
            taxonomy_samples=sample_refs_for(target, prefix="taxonomy"),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_sr_analysis",
    )

    semantic_release_root = Path(target.semantic_release_path)
    artifact_tree_root = Path(target.artifact_root_path)

    assert execution.status == "completed"
    assert llm.artifact_roots
    assert {root for _, root in llm.artifact_roots} == {str(semantic_release_root)}
    assert {
        "analyze_samples",
        "user_report_samples",
        "create_taxonomy_to_sample_analyses",
        "create_projections_to_sample_analyses",
    }.issubset({function_name for function_name, _ in llm.artifact_roots})
    assert (
        semantic_release_root
        / "tax_sa"
        / "wf_sr_analysis_taxonomy"
        / "tax_update.json"
    ).is_file()
    assert (
        semantic_release_root
        / "proj_sa"
        / "wf_sr_analysis_projection"
        / "tax_view.json"
    ).is_file()
    assert (
        semantic_release_root
        / "proj_sa"
        / "wf_sr_analysis_projection"
        / "proj_update.json"
    ).is_file()
    assert not (artifact_tree_root / "sample_analysis_requests").exists()
    assert not (artifact_tree_root / "taxonomy_to_sample_analysis_requests").exists()
    assert not (artifact_tree_root / "projection_to_sample_analysis_requests").exists()
    assert not (artifact_tree_root / "sa").exists()
    assert not (artifact_tree_root / "tax_sa").exists()
    assert not (artifact_tree_root / "proj_sa").exists()


def test_custom_taxonomy_promotion_slots_reach_projection_authoring_view_from_update_state(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = MinimalTaxonomyIdentityAdapter()
    llm = FakeLLMPort()

    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_custom_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=llm,
            taxonomy_samples=sample_refs_for(target, prefix="taxonomy"),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_slot_registry",
    )

    proposal_call = [payload for name, payload in llm.calls if name == "create_projections_to_sample_analyses"][0]
    view = proposal_call["taxonomy_authoring_view"]

    assert execution.status == "completed"
    assert [slot["slot"] for slot in view["promotion_slots"]] == ["counterparty", "amount_due"]
    assert [slot["slot"] for slot in execution.artifacts["taxonomy_ref"]["promotion_slots"]] == ["counterparty", "amount_due"]


def test_optional_analysis_report_failure_warns_without_blocking_custom_release(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter()

    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_custom_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=FakeLLMPort(fail_final="user_report_samples"),
            taxonomy_samples=sample_refs_for(target, prefix="taxonomy"),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_report_unavailable",
    )

    report_progress = [
        event
        for event in execution.progress_events
        if event["event_type"] == "llm_step" and event["step_id"].endswith("user_report_samples")
    ]
    warning_mirrors = [
        event
        for event in execution.mirror_events
        if event.get("severity") == "warning"
        and (event.get("technical_detail_ref") or {}).get("kind") == "analysis_report_unavailable"
    ]

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_active"
    assert report_progress
    assert {event["status"] for event in report_progress} == {"step_started", "completed"}
    assert all("unavailable" in event["user_visible_summary"] for event in report_progress if event["status"] == "completed")
    assert len(warning_mirrors) == 2
