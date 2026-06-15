from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_default_taxonomy_no_projections_final_notice_exposes_projectionless_completion_context(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_no_projections",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_projectionless_notice",
    )

    assert execution.status == "completed"
    final_event = [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"][-1]
    assert "default taxonomy-only Semantic Release state" in final_event["user_visible_summary"]
    assert target.artifact_root_path in final_event["user_visible_summary"]
    assert target.database_path in final_event["user_visible_summary"]
    assert str(execution.artifacts["projectionless_release_state_path"]) in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    assert "projectionless_release_state_path" in guidance["must_include"]
    assert guidance["next_step_instruction"]["mention_that_custom_projections_are_required"] is True

    completion = final_event.get("technical_detail_ref", {}).get("workflow_completion", {})
    assert completion["final_state"] == "semantic_release_incomplete"
    assert completion["outcome"]["taxonomy_present"] is True
    assert completion["outcome"]["projections_missing"] is True
    assert completion["outcome"]["semantic_release_runnable"] is False
    assert completion["outcome"]["database_ready_for_ingest"] is False
    assert completion["created_artifacts"]["projectionless_release_state_path"] == str(execution.artifacts["projectionless_release_state_path"])
    assert completion["kernel_persistence"]["attach_state_written"] is False
    assert completion["kernel_persistence"]["attach_state_archived_after_projection_strip"] is True
    assert [item["option_id"] for item in completion["next_step_options"]] == ["create_custom_projection_path"]
    assert completion["next_step_options"][0]["surface_availability"]["first_agent_tool"] == "kernel_resume_state"
    assert completion["next_step_options"][0]["surface_availability"]["continuation_workflow_tool"] == "create_custom_projection_path"


def test_custom_taxonomy_no_projections_final_notice_exposes_staged_taxonomy_context(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_custom_taxonomy_no_projections",
        runtime=runtime_for(
            tmp_path,
            target=target,
            llm_port=FakeLLMPort(),
            taxonomy_samples=sample_refs_for(target),
        ),
        workflow_run_id="wf_custom_projectionless_notice",
    )

    assert execution.status == "completed"
    marker = Path(target.semantic_release_path) / "incomplete_semantic_release.json"
    assert marker.is_file()
    final_event = [event for event in execution.mirror_events if event.get("event_type") == "workflow_completed"][-1]
    assert "staged custom taxonomy" in final_event["user_visible_summary"]
    assert target.artifact_root_path in final_event["user_visible_summary"]
    assert target.database_path in final_event["user_visible_summary"]
    assert "Semantic Release/staged/taxonomy/stage_taxonomy_001" in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_completion"
    assert "custom_taxonomy_stage_path" in guidance["must_include"]
    assert guidance["next_step_instruction"]["mention_that_custom_projections_are_required"] is True

    completion = final_event.get("technical_detail_ref", {}).get("workflow_completion", {})
    assert completion["final_state"] == "semantic_release_incomplete"
    assert completion["outcome"]["taxonomy_present"] is True
    assert completion["outcome"]["projections_missing"] is True
    assert completion["outcome"]["semantic_release_runnable"] is False
    assert completion["outcome"]["database_ready_for_ingest"] is False
    assert completion["created_artifacts"]["custom_taxonomy_stage_path"] == "Semantic Release/staged/taxonomy/stage_taxonomy_001"
    assert completion["kernel_persistence"]["attach_state_written"] is False
    assert completion["kernel_persistence"]["custom_taxonomy_staged"] is True
    assert [item["option_id"] for item in completion["next_step_options"]] == ["create_custom_projection_path"]
    assert completion["next_step_options"][0]["surface_availability"]["first_agent_tool"] == "kernel_resume_state"
    assert completion["next_step_options"][0]["surface_availability"]["continuation_workflow_tool"] == "create_custom_projection_path"
