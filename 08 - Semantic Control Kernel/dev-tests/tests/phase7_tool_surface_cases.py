from __future__ import annotations

import json

from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.surface.agent_tools import list_permanent_tools, model_visible_parameter_schema

from phase7_agent_invocation_support import isolated_state_paths


def test_every_permanent_tool_accepts_empty_model_visible_payload(tmp_path) -> None:
    service = AgentToolInvocationService(state_paths=isolated_state_paths(tmp_path))

    for definition in list_permanent_tools():
        result = service.invoke(definition.tool_name, invocation_context={}, model_payload={}).to_dict()
        assert result["schema_version"] == "agent_tool_result.v1"
        assert result["tool_name"] == definition.tool_name
        assert result["status"] in {"ok", "blocked"}
        assert "model_payload_rejected" not in str(result)


def test_live_workflow_handlers_replace_phase7_placeholder_blockers(tmp_path) -> None:
    service = AgentToolInvocationService(state_paths=isolated_state_paths(tmp_path))

    for definition in list_permanent_tools():
        result = service.invoke(definition.tool_name, invocation_context={}, model_payload={}).to_dict()
        assert "workflow_not_implemented" not in json.dumps(result, sort_keys=True)


def test_pipeline_run_is_internal_not_permanent_agent_tool(tmp_path) -> None:
    service = AgentToolInvocationService(state_paths=isolated_state_paths(tmp_path))

    result = service.invoke("pipeline_run", invocation_context={}, model_payload={}).to_dict()

    assert "pipeline_run" not in {definition.tool_name for definition in list_permanent_tools()}
    assert result["status"] == "rejected"
    assert result["effect"] == "none"
    assert result["error"]["code"] == "unknown_action"


def test_representative_workflow_tools_fail_closed_with_real_state_blockers(tmp_path) -> None:
    service = AgentToolInvocationService(state_paths=isolated_state_paths(tmp_path))
    waiting = service.invoke("empty_database_no_semantic_release", invocation_context={}, model_payload={}).to_dict()

    assert waiting["status"] == "ok"
    assert waiting["effect"] == "workflow_started"
    assert "Artifact Tree" in waiting["user_visible_summary"]

    removed = service.invoke("database_modify_taxonomy", invocation_context={}, model_payload={}).to_dict()
    assert removed["status"] == "rejected"
    assert removed["effect"] == "none"
    assert removed["error"]["code"] == "unknown_action"
    manual = service.invoke("manual_pipeline_run", invocation_context={}, model_payload={}).to_dict()
    assert manual["status"] == "ok"
    assert manual["effect"] == "workflow_started"
    assert "Artifact Tree" in manual["user_visible_summary"]
    rebuild = service.invoke("database_rebuild_from_artifacts", invocation_context={}, model_payload={}).to_dict()
    assert rebuild["status"] == "ok"
    assert rebuild["effect"] == "workflow_started"
    assert "Semantic Release" in rebuild["user_visible_summary"]
    merge = service.invoke("database_merge_additive_only", invocation_context={}, model_payload={}).to_dict()
    assert merge["status"] == "ok"
    assert merge["effect"] == "workflow_started"
    assert "number of source databases" in merge["user_visible_summary"]


def test_support_control_tools_return_phase7_result_shapes() -> None:
    service = AgentToolInvocationService()

    status = service.invoke("kernel_status", invocation_context={}, model_payload={}).to_dict()
    resume = service.invoke("kernel_resume_state", invocation_context={}, model_payload={}).to_dict()
    cancel = service.invoke("kernel_cancel_active_run", invocation_context={}, model_payload={}).to_dict()

    assert status["status"] == "ok"
    assert status["active_state"]["support_status"] == "read_only"
    assert resume["status"] == "ok"
    assert resume["resume_state"]["support_status"] == "read_only"
    assert cancel["status"] == "ok"
    assert cancel["cancel_status"] == "no_active_run"


def test_domain_values_are_rejected_from_context_or_model_payload() -> None:
    service = AgentToolInvocationService()

    from_context = service.invoke(
        "manual_pipeline_run",
        invocation_context={"client_injected": True, "artifact_root_path": "C:/tmp/artifacts"},
        model_payload={},
    ).to_dict()
    from_model = service.invoke(
        "kernel_status",
        invocation_context={"client_injected": True},
        model_payload={"database_name": "agent-authored-name"},
    ).to_dict()

    assert from_context["error"]["code"] == "model_payload_rejected"
    assert "artifact_root_path" in from_context["error"]["rejected_fields"]
    assert from_model["error"]["code"] == "model_payload_rejected"
    assert "database_name" in from_model["error"]["rejected_fields"]


def test_model_visible_parameter_schema_is_empty_and_closed() -> None:
    assert model_visible_parameter_schema() == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
