from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_started_route_writes_progress_receipts_and_mirror_events(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_progress",
    )
    paths = StatePaths.from_state_root(tmp_path / "state")

    assert execution.status == "completed"
    assert len(list((paths.events_progress_dir / "wf_progress").glob("*.json"))) >= len(execution.completed_step_ids)
    assert list(paths.receipts_operations_dir.glob("*.json"))
    assert list(paths.events_mirror_dir.glob("*.json"))


def test_no_semantic_release_final_notice_exposes_explain_now_completion_context(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_completion_notice",
    )

    assert execution.status == "completed"
    completion_events = [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"]
    assert completion_events
    final_event = completion_events[-1]
    assert "Artifact Tree and empty Corpus DB were created." in final_event["user_visible_summary"]
    assert target.artifact_root_path in final_event["user_visible_summary"]
    assert target.database_path in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    assert "artifact_root_path" in guidance["must_include"]
    assert "database_path" in guidance["must_include"]
    assert guidance["next_step_instruction"]["include_created_artifact_paths"] is True

    completion = final_event.get("technical_detail_ref", {}).get("workflow_completion", {})
    assert completion["final_state"] == "no_semantic_release"
    assert completion["workflow_explanation_context"]["schema_version"] == "kernel.workflow_explanation_context.v1"
    assert completion["workflow_explanation_context"]["already_available"] == []
    assert [item["fact_id"] for item in completion["workflow_explanation_context"]["performed_this_run"]] == [
        "artifact_tree_created",
        "empty_database_created",
    ]
    assert completion["outcome"]["artifact_tree_created"] is True
    assert completion["outcome"]["empty_database_created"] is True
    assert completion["outcome"]["database_ready_for_ingest"] is False
    assert completion["created_artifacts"]["artifact_root_path"] == target.artifact_root_path
    assert completion["created_artifacts"]["database_path"] == target.database_path
    assert completion["kernel_persistence"]["resume_state_written"] is True
    assert completion["next_step_options"][0]["option_id"] == "attach_default_semantic_release"
    assert completion["next_step_options"][0]["surface_availability"]["mode"] == "explicit_kernel_resume_selection"
    assert completion["next_step_options"][0]["surface_availability"]["direct_agent_tool_available"] is False
    assert completion["next_step_options"][0]["surface_availability"]["first_agent_tool"] == "kernel_resume_state"
    assert (
        completion["next_step_options"][0]["surface_availability"]["continuation_workflow_tool"]
        == "empty_database_default_taxonomy_default_projections"
    )
    assert completion["next_step_options"][1]["surface_availability"]["first_agent_tool"] == "kernel_resume_state"
    assert completion["next_step_options"][1]["surface_availability"]["direct_agent_tool_available"] is False
    assert completion["next_step_options"][1]["surface_availability"]["continuation_workflow_tool"] == "create_custom_taxonomy_path"
    assert completion["next_step_options"][1]["prerequisites"]["sample_evidence_required"] is True
    assert execution.progress_events[-1]["user_visible_summary"] == final_event["user_visible_summary"]


def test_default_ready_database_final_notice_exposes_explain_now_completion_context(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_default_ready_notice",
    )

    assert execution.status == "completed"
    final_event = [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"][-1]
    assert "ready for ingest" in final_event["user_visible_summary"]
    assert target.artifact_root_path in final_event["user_visible_summary"]
    assert target.database_path in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    assert "artifact_root_path" in guidance["must_include"]
    assert "database_path" in guidance["must_include"]
    assert guidance["next_step_instruction"]["include_created_artifact_paths"] is True

    completion = final_event.get("technical_detail_ref", {}).get("workflow_completion", {})
    assert completion["final_state"] == "semantic_release_active"
    assert completion["workflow_explanation_context"]["already_available"] == []
    assert "workflow_explanation_context_path" in guidance
    assert completion["outcome"]["artifact_tree_created"] is True
    assert completion["outcome"]["empty_database_created"] is True
    assert completion["outcome"]["semantic_release_attached"] is True
    assert completion["outcome"]["semantic_release_active"] is True
    assert completion["outcome"]["database_ready_for_ingest"] is True
    assert completion["kernel_persistence"]["attach_state_written"] is True
    assert completion["created_artifacts"]["artifact_root_path"] == target.artifact_root_path
    assert completion["created_artifacts"]["database_path"] == target.database_path
    assert completion["created_artifacts"]["default_release_path"]
    assert [item["option_id"] for item in completion["next_step_options"]] == [
        "manual_pipeline_run",
        "kernel_status",
    ]


def test_custom_projection_database_final_notice_exposes_explain_now_completion_context(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_custom_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            llm_port=FakeLLMPort(),
            projection_samples=sample_refs_for(target, prefix="projection"),
        ),
        workflow_run_id="wf_custom_projection_ready_notice",
    )

    assert execution.status == "completed"
    final_event = [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"][-1]
    assert final_event["user_visible_summary"] == (
        "Custom projection database creation is complete: Artifact Tree, empty Corpus DB, "
        "custom projections and active Semantic Release are ready."
    )

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    assert "performed_this_run" in guidance["preferred_structure"]
    assert "that a Kernel dialog is still waiting for input" in guidance["do_not_claim"]

    completion = final_event.get("technical_detail_ref", {}).get("workflow_completion", {})
    assert completion["final_state"] == "semantic_release_active"
    assert completion["outcome"]["database_ready_for_ingest"] is True
    assert completion["created_artifacts"]["custom_release_path"]
