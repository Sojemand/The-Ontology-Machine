from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server import support_monitor
from mcp_server.semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES
from mcp_server.tools import ToolFailure, call_tool, tool_definitions
from mcp_server.tool_visibility import kernel_syscall_context
from tests.tool_contract_cases import GOLDEN_CASES
from tests.tool_contract_matrix_fixtures import *
from tests.tool_contract_matrix_recorder import OwnerCallRecorder
from tests.tool_contract_matrix_types import GoldenCase


def _fake_kernel_catalog(_self, scope: str) -> dict[str, object]:
    assert scope == "permanent_agent"
    return {
        "schema_version": "semantic_control_kernel.mcp_tool_definition_list.v1",
        "scope": scope,
        "tool_definitions": [
            {
                "name": name,
                "description": name,
                "inputSchema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            }
            for name in PERMANENT_AGENT_TOOL_NAMES
        ],
    }


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: case.name)
def test_each_mcp_tool_has_a_governance_clean_golden_path(
    case: GoldenCase, mcp_files: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = OwnerCallRecorder(mcp_files)
    recorder.install(monkeypatch)
    monkeypatch.setattr(support_monitor, "state_root", lambda: Path(mcp_files["support_root"]))
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        _fake_kernel_catalog,
    )

    with kernel_syscall_context():
        result = call_tool(case.name, case.arguments(mcp_files))

    assert result["status"] in {
        "ok",
        "OK",
        "queued",
        "started",
        "idle",
        "no_documents_processed",
        "ready_to_run",
        "ready_for_new_database",
        "ready_for_empty_database",
        "ready_for_same_master_activation",
        "needs_user_decision",
        "no_change",
    }
    assert recorder.product_calls == case.product_calls(mcp_files)
    assert recorder.edit_calls == case.edit_calls(mcp_files)
    assert recorder.admin_calls == case.admin_calls(mcp_files)


def test_golden_matrix_cases_are_registered_non_kernel_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        _fake_kernel_catalog,
    )
    catalog_names = {str(tool["name"]) for tool in tool_definitions()}
    golden_names = {case.name for case in GOLDEN_CASES}

    assert golden_names <= catalog_names
    assert golden_names.isdisjoint(set(PERMANENT_AGENT_TOOL_NAMES))


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: case.name)
def test_each_mcp_tool_rejects_unknown_top_level_arguments(
    case: GoldenCase, mcp_files: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = OwnerCallRecorder(mcp_files)
    recorder.install(monkeypatch)
    monkeypatch.setattr(support_monitor, "state_root", lambda: Path(mcp_files["support_root"]))
    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_mcp_tool_definitions",
        _fake_kernel_catalog,
    )

    arguments = {**case.arguments(mcp_files), "__unexpected_extra__": True}

    with pytest.raises(ToolFailure, match="kennt diese Argumente|akzeptiert keine Argumente"):
        with kernel_syscall_context():
            call_tool(case.name, arguments)

    assert recorder.product_calls == []
    assert recorder.edit_calls == []
    assert recorder.admin_calls == []
