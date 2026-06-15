from __future__ import annotations

import shutil
from pathlib import Path

from _phase9_fakes import FakeSemanticReleaseAdapter, runtime_for, target_for
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_blocked_final_state_writes_resume_descriptor_and_state_summary(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter(missing_methods=["remove_taxonomy_or_projection"])
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_no_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_blocked_progress",
    )
    paths = StatePaths.from_state_root(tmp_path / "state")

    assert execution.status == "blocked"
    assert execution.resume_context is not None
    assert list(paths.resume_dir.glob("*.resume.json"))
    progress_text = "\n".join(path.read_text(encoding="utf-8") for path in (paths.events_progress_dir / "wf_blocked_progress").glob("*.json"))
    assert "semantic_release_complete_not_active" in progress_text
    assert (Path(target.semantic_release_path) / "incomplete_semantic_release.json").is_file()


def test_no_semantic_release_binding_conflict_exposes_explain_now_blocked_context(tmp_path) -> None:
    target = target_for(tmp_path, name="Artifact Tree Conflict", database_name="kernel_conflict")
    first_execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_binding_seed",
    )
    assert first_execution.status == "completed"

    shutil.rmtree(target.artifact_root_path)

    blocked_execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_binding_conflict_notice",
    )

    assert blocked_execution.status == "blocked"
    final_event = blocked_execution.mirror_events[-1]
    assert final_event["event_type"] == "blocker"
    assert "finished with unknown" not in final_event["user_visible_summary"]
    assert "empty database setup stopped before completion" in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_blocked"

    blocked = final_event.get("technical_detail_ref", {}).get("workflow_blocked", {})
    assert blocked["blocker"]["blocker_code"] == "binding_conflict"
    assert blocked["outcome"]["artifact_tree_created"] is True
    assert blocked["outcome"]["empty_database_created"] is False
    assert blocked["outcome"]["database_ready_for_ingest"] is False
    assert blocked["next_step_options"][0]["surface_availability"]["first_agent_tool"] == "empty_database_no_semantic_release"
    assert blocked_execution.progress_events[-1]["user_visible_summary"] == final_event["user_visible_summary"]


def test_default_taxonomy_no_projections_blocked_notice_exposes_projection_progress(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter(missing_methods=["remove_taxonomy_or_projection"])
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_no_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_projectionless_blocked_notice",
    )

    assert execution.status == "blocked"
    final_event = execution.mirror_events[-1]
    assert final_event["event_type"] == "blocker"
    assert "finished with unknown" not in final_event["user_visible_summary"]
    assert "projection removal did not complete" in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_blocked"

    blocked = final_event.get("technical_detail_ref", {}).get("workflow_blocked", {})
    assert blocked["blocker"]["blocker_code"] == "pipeline_capability_missing"
    assert blocked["database_exists"] is True
    assert blocked["release_already_exported"] is True
    assert blocked["release_already_written"] is True
    assert blocked["release_already_attached"] is True
    assert blocked["projection_removal_step_reached"] is True
    assert blocked["default_projections_removed"] is False
    assert blocked["outcome"]["database_ready_for_ingest"] is False
    assert blocked["next_step_options"][0]["surface_availability"]["first_agent_tool"] == "kernel_status"


def test_default_ready_database_blocked_notice_exposes_release_and_activation_progress(tmp_path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter(missing_methods=["activate_semantic_release"])
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_blocked_notice",
    )

    assert execution.status == "blocked"
    final_event = execution.mirror_events[-1]
    assert final_event["event_type"] == "blocker"
    assert "finished with unknown" not in final_event["user_visible_summary"]

    guidance = final_event.get("agent_explanation_guidance")
    assert isinstance(guidance, dict)
    assert guidance["response_mode"] == "explain_now"
    assert guidance["technical_detail_focus_path"] == "technical_detail_ref.workflow_blocked"

    blocked = final_event.get("technical_detail_ref", {}).get("workflow_blocked", {})
    assert blocked["blocker"]["blocker_code"] == "pipeline_capability_missing"
    assert blocked["database_exists"] is True
    assert blocked["release_already_exported"] is True
    assert blocked["release_already_written"] is True
    assert blocked["release_already_attached"] is True
    assert blocked["activation_failure_scope"]["activation_step_reached"] is True
    assert blocked["activation_failure_scope"]["preflight_after_attach_passed"] is True
    assert blocked["activation_failure_scope"]["owner_activation_call_started"] is True
    assert blocked["outcome"]["database_ready_for_ingest"] is False
