from __future__ import annotations

import json

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


def test_inspect_active_workspace_status_reports_missing_context(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: tmp_path / "missing-ui-state.json")
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: tmp_path / "mcp-runs")

    result = call_tool("inspect_active_workspace_status", {})

    assert result["status"] == "no_active_workspace"
    assert result["active_workspace"]["state_exists"] is False
    assert result["input"]["total_files"] == 0
    assert result["latest_run"]["status"] == "none"
    assert result["next_action"]["tool"] == "prepare_pipeline_workspace_root"


def test_inspect_active_workspace_status_reports_ready_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    input_dir, corpus_dir, db_path, ui_state_path = _workspace_fixture(tmp_path)
    (input_dir / "story.txt").write_text("Story input", encoding="utf-8")
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: tmp_path / "mcp-runs")

    result = call_tool("inspect_active_workspace_status", {})

    assert result["status"] == "ready_to_run"
    assert result["active_workspace"]["corpus_output_folder"] == str(corpus_dir)
    assert result["active_workspace"]["corpus_db_path"] == str(db_path)
    assert result["input"]["preview_files"][0]["relative_path"] == "story.txt"
    assert result["next_action"]["tool"] == "start_active_pipeline_run"


def test_inspect_current_environment_status_reports_canonical_fields(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    input_dir, corpus_dir, db_path, ui_state_path = _workspace_fixture(tmp_path)
    (input_dir / "story.txt").write_text("Story input", encoding="utf-8")
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: tmp_path / "mcp-runs")

    result = call_tool("inspect_current_environment_status", {})

    assert result["question_contract"] == "current_environment_status"
    assert result["source_of_truth"] == "orchestrator_ui_state"
    assert result["database_present"] is True
    assert result["database_path"] == str(db_path)
    assert result["workspace_present"] is True
    assert result["workspace_path"] == str(tmp_path / "workspace")
    assert result["input_folder_present"] is True
    assert result["input_file_count"] == 1
    assert result["next_safe_action"]["tool"] == "start_active_pipeline_run"


def test_inspect_active_workspace_status_prefers_running_run(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _workspace_fixture(tmp_path)
    runs_dir = tmp_path / "mcp-runs"
    run_dir = runs_dir / "run_live"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({"run_id": "run_live", "status": "running", "pid": 1234, "started_epoch": 1}), encoding="utf-8")

    class FakeProcess:
        pid = 1234

        def poll(self):
            return None

    tool_handlers._PIPELINE_RUN_PROCESSES.clear()
    tool_handlers._PIPELINE_RUN_PROCESSES["run_live"] = FakeProcess()
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: tmp_path / "orchestrator-state" / "ui_state.json")
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: runs_dir)

    result = call_tool("inspect_active_workspace_status", {})

    assert result["status"] == "running"
    assert result["latest_run"]["run_id"] == "run_live"
    assert result["next_action"]["tool"] == "inspect_active_pipeline_run"
    tool_handlers._PIPELINE_RUN_PROCESSES.clear()


def test_inspect_active_workspace_status_rejects_bad_preview_limit() -> None:
    with pytest.raises(ToolFailure, match="max_input_preview muss eine positive Ganzzahl"):
        call_tool("inspect_active_workspace_status", {"max_input_preview": 0})


def _workspace_fixture(tmp_path):
    input_dir = tmp_path / "workspace" / "Input"
    corpus_dir = tmp_path / "workspace" / "Corpus"
    input_dir.mkdir(parents=True)
    corpus_dir.mkdir()
    db_path = corpus_dir / "active.db"
    db_path.write_bytes(b"SQLite format 3\x00")
    ui_state_path = tmp_path / "orchestrator-state" / "ui_state.json"
    ui_state_path.parent.mkdir()
    ui_state_path.write_text(
        json.dumps(
            {
                "input_folder": str(input_dir),
                "artifact_folder": str(tmp_path / "workspace"),
                "corpus_output_folder": str(corpus_dir),
                "selected_corpus_db_path": str(db_path),
                "semantic_release_mode": "database_default",
            }
        ),
        encoding="utf-8",
    )
    return input_dir, corpus_dir, db_path, ui_state_path
