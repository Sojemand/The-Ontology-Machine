from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool

def test_cancel_active_pipeline_run_marks_run_cancelled(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "mcp-state" / "pipeline_runs" / "run_cancel"
    run_dir.mkdir(parents=True)
    response_path = run_dir / "response.json"
    snapshot_path = run_dir / "snapshot.json"
    snapshot_path.write_text(
        json.dumps({"is_running": True, "aborted": False, "total": 1, "completed": 0}),
        encoding="utf-8",
    )
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run_cancel",
                "status": "running",
                "pid": 888,
                "started_epoch": 1,
                "response_path": str(response_path),
                "snapshot_path": str(snapshot_path),
                "active_context": {},
            }
        ),
        encoding="utf-8",
    )

    class FakeProcess:
        pid = 888

        def __init__(self) -> None:
            self.return_code = None
            self.terminated = False

        def poll(self):
            return self.return_code

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout=None):
            self.return_code = -15
            return self.return_code

        def kill(self) -> None:
            self.return_code = -9

    process = FakeProcess()
    tool_handlers._PIPELINE_RUN_PROCESSES.clear()
    tool_handlers._PIPELINE_RUN_PROCESSES["run_cancel"] = process
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=tmp_path / "Orchestrator"))

    result = call_tool("cancel_active_pipeline_run", {"run_id": "run_cancel"})

    assert result["status"] == "cancelled"
    assert result["run_cancelled"] is True
    assert process.terminated is True
    assert "run_cancel" not in tool_handlers._PIPELINE_RUN_PROCESSES
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    response = json.loads(response_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "cancelled"
    assert response["status"] == "cancelled"
    assert snapshot["is_running"] is False
    assert snapshot["aborted"] is True

    inspected = call_tool("inspect_active_pipeline_run", {"run_id": "run_cancel"})
    assert inspected["status"] == "cancelled"
    assert inspected["run_phase"] == "cancelled"


def test_inspect_active_pipeline_run_returns_completed_result(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "mcp-state" / "pipeline_runs" / "run_done"
    run_dir.mkdir(parents=True)
    response_path = run_dir / "response.json"
    response_path.write_text(
        json.dumps({"status": "ok", "total": 2, "success": 2, "errors": 0, "needs_review": 0, "retries": 0}),
        encoding="utf-8",
    )
    snapshot_path = run_dir / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "total": 2,
                "completed": 1,
                "pending": 1,
                "success": 1,
                "errors": 0,
                "needs_review": 0,
                "current_file": "Fantasy Story.txt",
                "is_running": True,
                "stage_statuses": {
                    "Interpreter": {
                        "status": "Verarbeite...",
                        "detail": "Fantasy Story.txt",
                        "progress_current": 0,
                        "progress_total": 1,
                        "progress_label": "Requests",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run_done",
                "status": "running",
                "started_epoch": 1,
                "response_path": str(response_path),
                "snapshot_path": str(snapshot_path),
                "active_context": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=tmp_path / "Orchestrator"))

    result = call_tool("inspect_active_pipeline_run", {"run_id": "run_done"})

    assert result["status"] == "completed"
    assert result["run_result"]["success"] == 2
    assert result["snapshot"]["current_file"] == "Fantasy Story.txt"
    assert result["snapshot"]["stage_statuses"]["Interpreter"]["status"] == "Verarbeite..."


def test_inspect_active_pipeline_run_flags_zero_processed_documents_with_nonempty_input(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "mcp-state" / "pipeline_runs" / "run_zero"
    run_dir.mkdir(parents=True)
    response_path = run_dir / "response.json"
    response_path.write_text(
        json.dumps({"status": "ok", "total": 0, "success": 0, "errors": 0, "needs_review": 0, "retries": 0}),
        encoding="utf-8",
    )
    snapshot_path = run_dir / "snapshot.json"
    snapshot_path.write_text(
        json.dumps({"total": 0, "completed": 0, "success": 0, "errors": 0, "is_running": False, "stage_statuses": {}}),
        encoding="utf-8",
    )
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run_zero",
                "status": "running",
                "started_epoch": 1,
                "response_path": str(response_path),
                "snapshot_path": str(snapshot_path),
                "active_context": {},
                "input_before_run": {
                    "total_files": 2,
                    "preview_files": [
                        {"relative_path": "Fantasy Story.txt", "size_bytes": 13900},
                        {"relative_path": "Personal Story.txt", "size_bytes": 7438},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=tmp_path / "Orchestrator"))

    result = call_tool("inspect_active_pipeline_run", {"run_id": "run_zero"})

    assert result["status"] == "no_documents_processed"
    assert result["run_phase"] == "no_documents_processed"
    assert result["processing_started"] is False
    assert result["no_document_processing"]["input_files"] == 2
    assert result["run_result"]["status"] == "ok"
