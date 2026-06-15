from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES
from mcp_server.tools import call_tool
from mcp_server.tool_visibility import kernel_syscall_context

from .test_tool_handlers_corpus_reimport import _reimport_fixture


FORBIDDEN_KEYS = {
    "safe_next_kernel_workflows",
    "suggested_next_workflow_family_id",
    "safe_next_workflow_family_id",
    "next_workflow_family_id",
    "recommended_first_workflow_family_id",
    "related_workflow_family_ids",
}


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def test_support_surfaces_emit_canonical_kernel_tool_guidance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_list(_self, scope: str) -> dict[str, object]:
        assert scope == "permanent_agent"
        return {
            "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
            "scope": scope,
            "tool_definitions": [
                {"name": name, "description": name, "inputSchema": _empty_schema()}
                for name in PERMANENT_AGENT_TOOL_NAMES
            ],
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        fake_list,
    )

    known_names = {str(tool["name"]) for tool in tool_handlers.tool_definitions()}

    def fake_active_paths(_arguments: dict[str, Any]) -> list[Path]:
        return [Path("C:/tmp/story1.odt"), Path("C:/tmp/story2.odt")]

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        if module_key == "corpus_builder":
            return {
                "status": "ok",
                "detail": {
                    "release": {
                        "release_id": "fantasy.story.default",
                        "projection_ids": ["fantasy.story.default.v1"],
                        "projections": [{"projection_id": "fantasy.story.default.v1", "label": "Fantasy Story"}],
                    }
                },
            }
        if module_key == "orchestrator":
            path = payload["source_document_path"]
            return {
                "status": "ok",
                "source_document_path": path,
                "signals": {"filename": Path(path).name, "extension": ".odt", "estimated_document_type": "story"},
                "content_hints": {
                    "headings": [],
                    "field_like_phrases": ["household roles", "product categories"],
                    "candidate_markers": ["parents", "nanny", "mixes"],
                },
                "excerpt": {"chunks": ["My parents and the nanny were part of the household."]},
            }
        raise AssertionError(module_key)

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)
    monkeypatch.setattr(
        "mcp_server.tool_handler_source_sample_set_review.active_input_folder_sample_paths",
        fake_active_paths,
    )

    with kernel_syscall_context():
        document_review = call_tool(
            "review_source_document_taxonomy_coverage",
            {"source_document_path": "C:/tmp/story1.odt"},
        )
        sample_set_review = call_tool("review_source_sample_set_taxonomy_coverage", {})

    reimport_paths = _reimport_fixture(tmp_path, monkeypatch)
    preview = call_tool("preview_active_corpus_source_reimport", {})
    prepared = call_tool("prepare_active_corpus_source_reimport", {"user_confirmed": True})

    assert reimport_paths["input"].exists()
    for payload in (document_review, sample_set_review, preview, prepared):
        assert _forbidden_keys(payload) == set()
        assert set(payload["safe_next_kernel_tools"]) <= known_names
        assert "manual_pipeline_run" in payload["safe_next_kernel_tools"]

    assert document_review["compatibility_review"]["user_message_de"]
    assert document_review["working_release_refinement_request"]["requires_human_review"] is True
    assert sample_set_review["recommended_first_kernel_tool"] in {"create_custom_taxonomy_path", "create_custom_projection_path"}
    assert "database_rebuild_from_artifacts" in preview["safe_next_kernel_tools"]
    assert "database_rebuild_from_artifacts" in prepared["safe_next_kernel_tools"]


def test_bridge_handlers_call_canonical_surface_without_legacy_fallback(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_call_tool(self, **kwargs):
        calls.append(dict(kwargs))
        return {
            "schema_version": "semantic_control_kernel.mcp_response.v1",
            "status": "accepted",
            "tool_name": kwargs["tool_name"],
            "effect": "workflow_started",
            "user_visible_summary": "ok",
            "mirror_event": None,
            "error": None,
        }

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.call_tool",
        fake_call_tool,
    )

    status = call_tool("kernel_status", {})
    custom_taxonomy = call_tool("create_custom_taxonomy_path", {})

    assert status["tool_name"] == "kernel_status"
    assert custom_taxonomy["tool_name"] == "create_custom_taxonomy_path"
    assert [call["tool_name"] for call in calls] == ["kernel_status", "create_custom_taxonomy_path"]
    assert all(call["visibility"] == "agent_visible" for call in calls)
    assert all(call["model_arguments"] == {} for call in calls)
    assert "open_workflow" not in str(status)
    assert "inspect_workflow" not in str(custom_taxonomy)


def _forbidden_keys(payload: object) -> set[str]:
    seen: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key) in FORBIDDEN_KEYS:
                    seen.add(str(key))
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return seen
