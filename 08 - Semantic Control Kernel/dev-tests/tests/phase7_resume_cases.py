from __future__ import annotations

from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool

from _phase9_fakes import FakeLLMPort, runtime_for, sample_refs_for, target_for
from phase7_agent_invocation_support import isolated_state_paths


def test_kernel_resume_state_exposes_executable_resume_options(tmp_path, monkeypatch) -> None:
    state_paths = isolated_state_paths(tmp_path)
    target = target_for(tmp_path)
    runtimes = [
        runtime_for(tmp_path, target=target),
        runtime_for(tmp_path),
    ]

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._database_creation_runtime",
        lambda _state_paths: runtimes.pop(0),
    )

    initial = dispatch_permanent_workflow_tool("empty_database_no_semantic_release", state_paths=state_paths).to_dict()
    service = AgentToolInvocationService(state_paths=state_paths)
    resume = service.invoke("kernel_resume_state", invocation_context={}, model_payload={}).to_dict()

    options = resume["resume_state"]["resume_options"]
    default_option = next(
        option
        for option in options
        if option["continuation_workflow_tool"] == "empty_database_default_taxonomy_default_projections"
    )

    assert initial["final_state"] == "no_semantic_release"
    assert resume["resume_state"]["next_agent_tool"] == "kernel_continue_resumable_workflow"
    assert default_option["schema_version"] == "kernel.resume_option.v1"
    assert default_option["agent_tool"] == "kernel_continue_resumable_workflow"
    assert default_option["resume_option_ref"].startswith("opaque:")
    assert default_option["target_summary"]["database_name"] == target.database_name

    continued = service.invoke(
        "kernel_continue_resumable_workflow",
        invocation_context={},
        model_payload={"resume_option_ref": default_option["resume_option_ref"]},
    ).to_dict()

    assert continued["status"] == "ok"
    assert continued["effect"] == "workflow_completed"
    assert continued["continued_workflow_tool"] == "empty_database_default_taxonomy_default_projections"
    assert continued["final_state"] == "semantic_release_active"
    assert WorkflowResumeStore(state_paths).list_resumable() == []


def test_kernel_resume_state_custom_taxonomy_continuation_persists_projection_followup(tmp_path, monkeypatch) -> None:
    state_paths = isolated_state_paths(tmp_path)
    target = target_for(tmp_path)
    runtime = runtime_for(
        tmp_path,
        target=target,
        llm_port=FakeLLMPort(),
        taxonomy_samples=sample_refs_for(target),
    )

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._database_creation_runtime",
        lambda _state_paths: runtime,
    )

    initial = dispatch_permanent_workflow_tool("empty_database_no_semantic_release", state_paths=state_paths).to_dict()
    service = AgentToolInvocationService(state_paths=state_paths)
    resume = service.invoke("kernel_resume_state", invocation_context={}, model_payload={}).to_dict()
    custom_option = next(
        option
        for option in resume["resume_state"]["resume_options"]
        if option["continuation_workflow_tool"] == "create_custom_taxonomy_path"
    )

    continued = service.invoke(
        "kernel_continue_resumable_workflow",
        invocation_context={},
        model_payload={"resume_option_ref": custom_option["resume_option_ref"]},
    ).to_dict()

    assert initial["final_state"] == "no_semantic_release"
    assert continued["status"] == "ok"
    assert continued["effect"] == "workflow_completed"
    assert continued["continued_workflow_tool"] == "create_custom_taxonomy_path"
    assert continued["final_state"] == "semantic_release_incomplete"
    assert continued["resume_state"]["next_step_id"] == "proj_require_taxonomy"
    assert continued["resume_state"]["allowed_continuation_workflow_tools"] == ["create_custom_projection_path"]
    completion = continued["mirror_event"]["technical_detail_ref"]["workflow_completion"]
    assert "Previously available workflow state was reused" in continued["mirror_event"]["user_visible_summary"]
    assert [item["fact_id"] for item in completion["workflow_explanation_context"]["already_available"]] == [
        "artifact_tree_created",
        "empty_database_created",
    ]
    assert completion["outcome"]["projections_missing"] is True
    assert completion["kernel_persistence"]["custom_taxonomy_staged"] is True
