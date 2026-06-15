from __future__ import annotations

from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool

from _phase9_fakes import runtime_for, target_for
from phase7_agent_invocation_support import isolated_state_paths


def test_phase9_dispatch_preserves_resume_state_for_resumable_completion(tmp_path, monkeypatch) -> None:
    state_paths = isolated_state_paths(tmp_path)
    target = target_for(tmp_path)
    runtime = runtime_for(tmp_path, target=target)

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._database_creation_runtime",
        lambda _state_paths: runtime,
    )

    result = dispatch_permanent_workflow_tool(
        "empty_database_default_taxonomy_no_projections",
        state_paths=state_paths,
    ).to_dict()

    assert result["status"] == "ok"
    assert result["final_state"] == "semantic_release_incomplete"
    assert result["resume_state"]["next_step_id"] == "proj_require_taxonomy"
    assert result["resume_state"]["allowed_continuation_workflow_tools"] == ["create_custom_projection_path"]
    assert result["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    completion = result["mirror_event"]["technical_detail_ref"]["workflow_completion"]
    assert completion["outcome"]["taxonomy_present"] is True
    assert completion["outcome"]["projections_missing"] is True
    assert completion["next_step_options"][0]["surface_availability"]["continuation_workflow_tool"] == "create_custom_projection_path"


def test_phase9_dispatch_starts_new_creation_instead_of_implicit_resume(tmp_path, monkeypatch) -> None:
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
    fresh = dispatch_permanent_workflow_tool(
        "empty_database_default_taxonomy_default_projections",
        state_paths=state_paths,
    ).to_dict()

    assert initial["status"] == "ok"
    assert initial["final_state"] == "no_semantic_release"
    assert "empty_database_default_taxonomy_default_projections" in initial["resume_state"]["allowed_continuation_workflow_tools"]
    assert initial["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    assert target.artifact_root_path in initial["mirror_event"]["user_visible_summary"]
    assert target.database_path in initial["mirror_event"]["user_visible_summary"]
    assert fresh["status"] == "blocked"
    assert fresh["error"]["code"] == "input_missing"
    assert fresh["active_state"]["blocked_step_id"] == "dc_collect_target"

    resumable = WorkflowResumeStore(state_paths).list_resumable()
    assert [state.payload["workflow_run_id"] for state in resumable] == [initial["workflow_run_id"]]


def test_direct_creation_continuation_invocation_blocks_without_creating_recovery_state(tmp_path) -> None:
    state_paths = isolated_state_paths(tmp_path)
    state_paths.ensure_layout()

    for tool_name in ("create_custom_taxonomy_path", "create_custom_projection_path"):
        result = dispatch_permanent_workflow_tool(tool_name, state_paths=state_paths).to_dict()

        assert result["status"] == "blocked"
        assert result["effect"] == "none"
        assert result["error"]["code"] == "continuation_requires_resume_option"
        assert result["active_state"]["next_agent_tool"] == "kernel_continue_resumable_workflow"
    assert not list(state_paths.events_progress_dir.iterdir())
    assert not list(state_paths.events_recovery_dir.iterdir())
    assert not list(state_paths.events_tool_availability_dir.iterdir())


def test_phase9_dispatch_returns_default_ready_completion_mirror_event(tmp_path, monkeypatch) -> None:
    state_paths = isolated_state_paths(tmp_path)
    target = target_for(tmp_path)
    runtime = runtime_for(tmp_path, target=target)

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._database_creation_runtime",
        lambda _state_paths: runtime,
    )

    result = dispatch_permanent_workflow_tool(
        "empty_database_default_taxonomy_default_projections",
        state_paths=state_paths,
    ).to_dict()

    assert result["status"] == "ok"
    assert result["final_state"] == "semantic_release_active"
    assert result["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    assert target.artifact_root_path in result["mirror_event"]["user_visible_summary"]
    assert target.database_path in result["mirror_event"]["user_visible_summary"]
