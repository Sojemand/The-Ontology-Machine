from __future__ import annotations

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, runtime_for, sample_refs_for, target_for
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_phase9_taxonomy_path_emits_sample_analysis_report_mirror(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "create_custom_taxonomy_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=FakeSemanticReleaseAdapter(),
            llm_port=FakeLLMPort(),
            taxonomy_samples=sample_refs_for(target),
        ),
        workflow_run_id="wf_taxonomy_report",
    )

    report_events = [
        event
        for event in execution.mirror_events
        if isinstance(event.get("agent_explanation_guidance"), dict)
        and event["agent_explanation_guidance"].get("response_mode") == "emit_direct_message"
    ]

    assert execution.status == "completed"
    assert report_events
    assert "Sample analysis report." in report_events[0]["user_visible_summary"]
