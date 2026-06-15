from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_inspect_active_pipeline_run_marks_lost_running_process_interrupted(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = _lost_run_dir(tmp_path, "run_lost", pid=777)
    tool_handlers._PIPELINE_RUN_PROCESSES.clear()
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=tmp_path / "Orchestrator"))

    result = call_tool("inspect_active_pipeline_run", {"run_id": "run_lost"})

    assert result["status"] == "interrupted"
    assert result["run_phase"] == "interrupted"
    assert "neu" in result["message"] or "verloren" in result["message"]
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "interrupted"
    assert metadata["interruption_reason"]


def test_cancel_active_pipeline_run_reports_lost_running_process_interrupted(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = _lost_run_dir(tmp_path, "run_lost_cancel", pid=778)
    tool_handlers._PIPELINE_RUN_PROCESSES.clear()
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)

    result = call_tool("cancel_active_pipeline_run", {"run_id": "run_lost_cancel"})

    assert result["status"] == "interrupted"
    assert result["run_cancelled"] is False
    assert "nicht mehr abbrechbar" in result["message"]
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "interrupted"


def _lost_run_dir(tmp_path, run_id: str, *, pid: int):
    run_dir = tmp_path / "mcp-state" / "pipeline_runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "running",
                "pid": pid,
                "started_epoch": 1,
                "active_context": {},
            }
        ),
        encoding="utf-8",
    )
    return run_dir
