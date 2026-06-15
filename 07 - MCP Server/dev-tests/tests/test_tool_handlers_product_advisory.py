from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_explain_pipeline_capabilities_answers_database_orientation() -> None:
    result = call_tool(
        "explain_pipeline_capabilities",
        {"question": "Was kann ich alles mit der Datenbank tun?"},
    )

    assert result["question_contract"] == "pipeline_product_advisory"
    assert result["advisory_mode"] == "capabilities"
    assert any(card["concept_id"] == "database" for card in result["concept_cards"])
    assert result["goal_playbooks"][0]["playbook_id"] == "what_can_i_do"
    assert "kernel_status" in result["safe_next_kernel_tools"]
    assert "search_corpus" in result["safe_next_mcp_tools"]
    assert _legacy_workflow_keys(result) == set()


def test_recommend_next_steps_prefers_sample_set_for_new_document_kind() -> None:
    result = call_tool(
        "recommend_pipeline_next_steps",
        {"goal": "Ich habe mehrere neue Dokumente und die Datenbank soll diese Art Dokumente gut abbilden."},
    )

    path = result["recommended_path"]
    assert result["question_contract"] == "pipeline_product_advisory"
    assert path["first_kernel_tool"] == "create_custom_taxonomy_path"
    assert "Overfitting" in path["why_de"]
    assert "create_custom_projection_path" in result["safe_next_kernel_tools"]
    assert _legacy_workflow_keys(result) == set()


def test_inspect_product_context_includes_workspace_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "Input"
    artifact_root = tmp_path / "Artifacts"
    corpus_root = artifact_root / "Corpus"
    orchestrator_root = tmp_path / "Orchestrator"
    input_root.mkdir()
    corpus_root.mkdir(parents=True)
    db_path = corpus_root / "active.db"
    db_path.write_bytes(b"")
    (input_root / "story.txt").write_text("sample", encoding="utf-8")
    ui_state_path = orchestrator_root / "state" / "ui_state.json"
    _write_json(
        ui_state_path,
        {
            "input_folder": str(input_root),
            "artifact_folder": str(artifact_root),
            "corpus_output_folder": str(corpus_root),
            "selected_corpus_db_path": str(db_path),
            "semantic_release_mode": "database_default",
        },
    )
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=orchestrator_root))
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)

    result = call_tool("inspect_pipeline_product_context", {"max_workflows": 4})

    assert result["question_contract"] == "pipeline_product_advisory"
    assert result["current_environment"]["database_present"] is True
    assert result["current_environment"]["input_file_count"] == 1
    assert result["kernel_tool_summary"]["tool_count"] == 4
    assert "manual_pipeline_run" in result["safe_next_kernel_tools"]
    assert result["safe_next_mcp_tools"] == ["inspect_current_environment_status"]
    assert _legacy_workflow_keys(result) == set()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _legacy_workflow_keys(payload: object) -> set[str]:
    forbidden = {
        "workflow_catalog_summary",
        "safe_next_kernel_workflows",
        "recommended_first_workflow_family_id",
        "related_workflow_family_ids",
        "first_workflow_family_id",
        "workflow_family_id",
    }
    seen: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key) in forbidden:
                    seen.add(str(key))
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return seen
