from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mcp_server import support_monitor, tool_handlers, tool_handlers_pipeline_run
from mcp_server.contract_client import ContractError
from mcp_server.tools import ToolFailure, call_tool

def test_run_active_pipeline_loads_saved_context_and_runs_batch(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    artifact_root = tmp_path / "Artifacts"
    input_root = artifact_root / "Input"
    corpus_root = artifact_root / "Corpus"
    input_root.mkdir(parents=True)
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()
    (input_root / "story.txt").write_text("Once upon a moon.", encoding="utf-8")
    state_path = tmp_path / "Orchestrator" / "state" / "ui_state.json"
    state_path.parent.mkdir(parents=True)
    state = {
        "input_folder": str(input_root),
        "artifact_folder": str(artifact_root),
        "corpus_output_folder": str(corpus_root),
        "selected_corpus_db_path": str(corpus_db),
        "semantic_release_mode": "database_default",
        "semantic_release_path": "",
        "mode": "single",
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    calls: list[tuple[str, dict[str, Any], int | None]] = []

    def fake_module_spec(module_key: str):
        assert module_key == "orchestrator"
        return SimpleNamespace(root=state_path.parents[1])

    def fake_product(module_key: str, payload: dict[str, Any], *, timeout: int | None = None) -> dict[str, Any]:
        calls.append((module_key, payload, timeout))
        return {"status": "ok", "total": 1, "success": 1, "errors": 0, "needs_review": 0, "retries": 0}

    monkeypatch.setattr(tool_handlers, "module_spec", fake_module_spec)
    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    result = call_tool("run_active_pipeline", {})

    assert result["status"] == "ok"
    assert result["mode"] == "batch"
    assert result["input_before_run"]["total_files"] == 1
    assert calls == [
        (
            "orchestrator",
            {"action": "run", "ui_state": {**state, "mode": "batch"}},
            3600,
        )
    ]


def test_run_active_pipeline_reports_empty_input_without_starting(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    artifact_root = tmp_path / "Artifacts"
    input_root = artifact_root / "Input"
    corpus_root = artifact_root / "Corpus"
    input_root.mkdir(parents=True)
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()
    state_path = tmp_path / "Orchestrator" / "state" / "ui_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "input_folder": str(input_root),
                "artifact_folder": str(artifact_root),
                "corpus_output_folder": str(corpus_root),
                "selected_corpus_db_path": str(corpus_db),
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=state_path.parents[1]))
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    result = call_tool("run_active_pipeline", {})

    assert result["status"] == "no_input_files"
    assert result["run_started"] is False
    assert calls == []


def test_run_active_pipeline_flags_zero_processed_documents_with_nonempty_input(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    artifact_root = tmp_path / "Artifacts"
    input_root = artifact_root / "Input"
    corpus_root = artifact_root / "Corpus"
    input_root.mkdir(parents=True)
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()
    (input_root / "story.txt").write_text("Once upon a moon.", encoding="utf-8")
    state_path = tmp_path / "Orchestrator" / "state" / "ui_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "input_folder": str(input_root),
                "artifact_folder": str(artifact_root),
                "corpus_output_folder": str(corpus_root),
                "selected_corpus_db_path": str(corpus_db),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=state_path.parents[1]))
    monkeypatch.setattr(
        tool_handlers,
        "_invoke_product",
        lambda _module_key, _payload, **_kwargs: {"status": "ok", "total": 0, "success": 0, "errors": 0, "needs_review": 0, "retries": 0},
    )

    result = call_tool("run_active_pipeline", {})

    assert result["status"] == "no_documents_processed"
    assert result["run_started"] is True
    assert result["processing_started"] is False
    assert result["no_document_processing"]["input_files"] == 1


def test_start_active_pipeline_run_returns_run_id_without_waiting(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    artifact_root = tmp_path / "Artifacts"
    input_root = artifact_root / "Input"
    corpus_root = artifact_root / "Corpus"
    input_root.mkdir(parents=True)
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "Fantasie.db"
    sqlite3.connect(corpus_db).close()
    (input_root / "story.txt").write_text("Once upon a moon.", encoding="utf-8")
    state_path = tmp_path / "Orchestrator" / "state" / "ui_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "input_folder": str(input_root),
                "artifact_folder": str(artifact_root),
                "corpus_output_folder": str(corpus_root),
                "selected_corpus_db_path": str(corpus_db),
                "mode": "single",
            }
        ),
        encoding="utf-8",
    )
    popen_calls: list[tuple[list[str], Path, dict[str, Any]]] = []

    class FakeProcess:
        pid = 777

        def poll(self):
            return None

    def fake_module_spec(module_key: str):
        assert module_key == "orchestrator"
        return SimpleNamespace(
            root=state_path.parents[1],
            python_executable=Path("python.exe"),
            contract_module="orchestrator.orchestrator_contract",
            runtime_dir=tmp_path / "runtime",
        )

    def fake_popen(args, *, cwd, **_kwargs):
        popen_calls.append((list(args), Path(cwd), dict(_kwargs)))
        return FakeProcess()

    runs_dir = tmp_path / "mcp-runs"
    monkeypatch.setattr(tool_handlers, "module_spec", fake_module_spec)
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: runs_dir)
    monkeypatch.setattr(
        tool_handlers_pipeline_run,
        "subprocess",
        type("_PipelineRunSubprocess", (), {"Popen": staticmethod(fake_popen)}),
    )

    result = call_tool("start_active_pipeline_run", {})

    assert result["status"] == "started"
    assert result["pid"] == 777
    assert result["input_before_run"]["total_files"] == 1
    assert popen_calls[0][1] == state_path.parents[1]
    assert popen_calls[0][2]["stdin"] is subprocess.DEVNULL
    assert popen_calls[0][2]["close_fds"] is True
    run_dir = runs_dir / result["run_id"]
    request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert request["snapshot_path"] == str(run_dir / "snapshot.json")
    assert metadata["snapshot_path"] == str(run_dir / "snapshot.json")
