from __future__ import annotations

from _phase9_fakes import FakeLLMPort, load_default_release_fixture, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_custom_projection_path_emits_llm_progress_events_between_kernel_steps(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            llm_port=FakeLLMPort(),
            projection_samples=sample_refs_for(target, prefix="projection"),
            taxonomy_ref=load_default_release_fixture()["taxonomy_ref"],
        ),
        workflow_run_id="wf_projection_llm_progress",
        initial_final_state="semantic_release_active",
    )

    llm_events = [event for event in execution.progress_events if event["event_type"] == "llm_step"]
    llm_functions = [
        event["artifact_refs"][0]["llm_function_name"]
        for event in llm_events
        if event.get("artifact_refs")
    ]

    assert execution.status == "completed"
    assert llm_functions == [
        "analyze_samples",
        "analyze_samples",
        "user_report_samples",
        "user_report_samples",
        "create_projections_to_sample_analyses",
        "create_projections_to_sample_analyses",
    ]
    assert llm_events[0]["status"] == "step_started"
    assert llm_events[1]["status"] == "completed"
    assert [event["step_id"] for event in llm_events] == [
        "llm_projection_analyze_samples",
        "llm_projection_analyze_samples",
        "llm_projection_user_report_samples",
        "llm_projection_user_report_samples",
        "llm_projection_create_projections_to_sample_analyses",
        "llm_projection_create_projections_to_sample_analyses",
    ]
    assert "LLM call analyze_samples started" in llm_events[0]["user_visible_summary"]
    assert "LLM call analyze_samples completed" in llm_events[1]["user_visible_summary"]
    assert all(event["step_id"].startswith("llm_") for event in llm_events)
