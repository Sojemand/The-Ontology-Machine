from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.contract_client import ModuleSpec
from mcp_server.tools import ToolFailure, call_tool, tool_definitions
from tests.tool_contract_matrix_recorder import OwnerCallRecorder
from tests.tool_subprocess_fixtures import *


def test_corpus_builder_edit_tools_are_first_class_catalog_entries() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    assert {
        "corpus_builder.describe_surfaces",
        "corpus_builder.read_surface",
        "corpus_builder.validate_surface",
        "corpus_builder.write_surface",
    } <= set(tools)
    assert tools["corpus_builder.describe_surfaces"]["inputSchema"]["properties"] == {}
    assert set(tools["corpus_builder.read_surface"]["inputSchema"]["required"]) == {"surface_id"}
    assert set(tools["corpus_builder.validate_surface"]["inputSchema"]["required"]) == {"surface_id", "value"}
    assert set(tools["corpus_builder.write_surface"]["inputSchema"]["required"]) == {"surface_id", "value"}


def test_corpus_builder_edit_tools_delegate_to_owner_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = OwnerCallRecorder({})
    recorder.install(monkeypatch)

    call_tool("corpus_builder.describe_surfaces", {})
    call_tool("corpus_builder.read_surface", {"surface_id": "corpus_builder.settings"})
    call_tool(
        "corpus_builder.validate_surface",
        {"surface_id": "corpus_builder.embeddings_policy", "value": {"embeddings.dimensions": 1536}},
    )
    call_tool(
        "corpus_builder.write_surface",
        {"surface_id": "corpus_builder.search_policy", "value": {"fulltext.limit_default": 10}},
    )

    assert recorder.edit_calls == [
        ("corpus_builder", {"action": "describe_surfaces"}),
        ("corpus_builder", {"action": "read_surface", "surface_id": "corpus_builder.settings"}),
        (
            "corpus_builder",
            {
                "action": "validate_surface",
                "surface_id": "corpus_builder.embeddings_policy",
                "value": {"embeddings.dimensions": 1536},
            },
        ),
        (
            "corpus_builder",
            {
                "action": "write_surface",
                "surface_id": "corpus_builder.search_policy",
                "value": {"fulltext.limit_default": 10},
            },
        ),
    ]
    assert recorder.product_calls == []
    assert recorder.admin_calls == []


def test_corpus_builder_edit_tools_reject_extra_arguments_before_owner_call(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = OwnerCallRecorder({})
    recorder.install(monkeypatch)

    with pytest.raises(ToolFailure, match="akzeptiert keine Argumente"):
        call_tool("corpus_builder.describe_surfaces", {"surface_id": "corpus_builder.settings"})

    assert recorder.edit_calls == []


@pytest.mark.integration
def test_corpus_builder_edit_surfaces_use_real_contract_and_exclude_runtime_artifacts(
    isolated_owner_specs: dict[str, ModuleSpec],
) -> None:
    corpus_root = isolated_owner_specs["corpus_builder"].root
    described = call_tool("corpus_builder.describe_surfaces", {})

    assert described["status"] == "ok"
    assert [item["surface_id"] for item in described["surfaces"]] == [
        "corpus_builder.settings",
        "corpus_builder.embeddings_policy",
        "corpus_builder.search_policy",
    ]
    assert {item["source_path"] for item in described["surfaces"]} == {
        "config/corpus_config.json",
        "config/search_policy.json",
    }
    assert all(item["editable"] is True for item in described["surfaces"])
    assert not any(str(item["source_path"]).startswith(("runtime/", "state/", "output/")) for item in described["surfaces"])

    settings = call_tool("corpus_builder.read_surface", {"surface_id": "corpus_builder.settings"})
    missing = call_tool("corpus_builder.read_surface", {"surface_id": "corpus_builder.semantic_release_default"})
    debug_write = call_tool(
        "corpus_builder.write_surface",
        {"surface_id": "corpus_builder.debug_capabilities", "value": {"module_key": "override"}},
    )

    assert settings["status"] == "ok"
    assert settings["value"]["database.corpus_db"]
    assert missing["status"] == "error"
    assert "Unbekannte Surface" in missing["reason"]
    assert debug_write["status"] == "error"
    assert "Unbekannte Surface" in debug_write["reason"]
    assert (corpus_root / "module-manifest.json").exists()


@pytest.mark.integration
def test_corpus_builder_validate_does_not_write_and_write_validates(
    isolated_owner_specs: dict[str, ModuleSpec],
) -> None:
    corpus_root = isolated_owner_specs["corpus_builder"].root
    config_path = corpus_root / "config" / "corpus_config.json"
    current = call_tool("corpus_builder.read_surface", {"surface_id": "corpus_builder.embeddings_policy"})
    value = dict(current["value"])
    value["embeddings.batch_size"] = int(value["embeddings.batch_size"]) + 1

    before_validate = config_path.read_text(encoding="utf-8")
    validated = call_tool(
        "corpus_builder.validate_surface",
        {"surface_id": "corpus_builder.embeddings_policy", "value": value},
    )
    after_validate = config_path.read_text(encoding="utf-8")
    invalid = dict(value)
    invalid["embeddings.dimensions"] = 0
    rejected = call_tool(
        "corpus_builder.write_surface",
        {"surface_id": "corpus_builder.embeddings_policy", "value": invalid},
    )
    after_rejected_write = config_path.read_text(encoding="utf-8")
    written = call_tool(
        "corpus_builder.write_surface",
        {"surface_id": "corpus_builder.embeddings_policy", "value": value},
    )

    assert validated["status"] == "ok"
    assert before_validate == after_validate
    assert rejected["status"] == "error"
    assert "positive Ganzzahl" in rejected["reason"]
    assert after_rejected_write == after_validate
    assert written["status"] == "ok"
    assert written["value"] == value
    assert config_path.read_text(encoding="utf-8") != before_validate
