from __future__ import annotations

from _phase9_fakes import runtime_for, target_for
from semantic_control_kernel.workflows.database_creation.resume import resume_inputs_for_tool
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_no_release_resume_can_continue_into_default_release_activation(tmp_path) -> None:
    target = target_for(tmp_path)
    initial = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_no_release_to_default",
    )

    assert initial.resume_context is not None
    target_resume, initial_artifacts, initial_final_state, initial_completed_step_ids = resume_inputs_for_tool(
        "empty_database_default_taxonomy_default_projections",
        initial.resume_context,
    )

    resumed = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path),
        workflow_run_id="wf_default_release_resume",
        target=target_resume,
        initial_artifacts=initial_artifacts,
        initial_final_state=initial_final_state,
        initial_completed_step_ids=initial_completed_step_ids,
    )

    assert resumed.status == "completed"
    assert resumed.final_state == "semantic_release_active"
    assert resumed.completed_step_ids[:4] == [
        "dc_collect_target",
        "dc_create_artifact_tree",
        "dc_store_artifact_tree",
        "dc_create_empty_database",
    ]
    assert resumed.completed_step_ids_at_run_start == list(initial_completed_step_ids)
    assert resumed.to_dict()["completed_step_ids_this_run"] == [
        "dc_export_default_release",
        "dc_write_default_release",
        "dc_attach_default_release",
        "dc_activate_default_release",
        "dc_final_notice",
    ]

    final_event = [event for event in resumed.mirror_events if event.get("event_type") == "workflow_completed"][-1]
    assert "Previously available workflow state was reused: Artifact Tree and empty Corpus DB." in final_event["user_visible_summary"]
    assert "Artifact Tree, empty Corpus DB and the complete default Semantic Release were created" not in final_event["user_visible_summary"]
    completion = final_event["technical_detail_ref"]["workflow_completion"]
    explanation_context = completion["workflow_explanation_context"]
    assert explanation_context["schema_version"] == "kernel.workflow_explanation_context.v1"
    assert explanation_context["completed_step_ids_at_run_start"] == list(initial_completed_step_ids)
    assert [item["fact_id"] for item in explanation_context["already_available"]] == [
        "artifact_tree_created",
        "empty_database_created",
    ]
    assert [item["fact_id"] for item in explanation_context["performed_this_run"]] == [
        "default_semantic_release_exported",
        "default_semantic_release_written",
        "default_semantic_release_attached",
        "default_semantic_release_activated",
    ]
    guidance = final_event["agent_explanation_guidance"]
    assert guidance["preferred_structure"][:2] == ["already_available", "performed_this_run"]
    assert "already_available" in guidance["must_distinguish_provenance"]
