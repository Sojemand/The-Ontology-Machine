from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_inspect_active_pipeline_run_marks_healthcheck_failure_as_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "mcp-state" / "pipeline_runs" / "run_preflight"
    run_dir.mkdir(parents=True)
    response_path = run_dir / "response.json"
    response_path.write_text(
        json.dumps({"status": "error", "reason": "Healthcheck fehlgeschlagen: Optimizer: Timeout"}),
        encoding="utf-8",
    )
    orchestrator_root = tmp_path / "Orchestrator"
    log_dir = orchestrator_root / "state" / "pipeline" / "runs" / "2026-04-25T06-17-01"
    log_dir.mkdir(parents=True)
    (log_dir / "run.log").write_text("Run gestartet\n[HEALTH-FEHLER] Healthcheck fehlgeschlagen\n", encoding="utf-8")
    (log_dir / "healthcheck.failure.json").write_text(
        json.dumps(
            {
                "scope": "pipeline_run",
                "results": [
                    {
                        "key": "optimizer",
                        "display_name": "Optimizer",
                        "healthy": False,
                        "message": "Optimizer hat das Zeitlimit (30s) ueberschritten.",
                        "dependencies": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run_preflight",
                "status": "running",
                "started_epoch": 1,
                "response_path": str(response_path),
                "active_context": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tool_handlers, "_pipeline_runs_dir", lambda: run_dir.parent)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=orchestrator_root))

    result = call_tool("inspect_active_pipeline_run", {"run_id": "run_preflight"})

    assert result["status"] == "error"
    assert result["run_phase"] == "preflight_failed"
    assert result["processing_started"] is False
    assert result["preflight_failure"]["modules"][0]["display_name"] == "Optimizer"
    assert result["preflight_failure"]["artifact_path"].endswith("healthcheck.failure.json")
