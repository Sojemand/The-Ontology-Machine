from __future__ import annotations

from pathlib import Path

from orchestrator.models import UiState
import orchestrator.worker as worker_module
from orchestrator.worker import run_worker_process
from tests.worker_process_support import EventStub as _EventStub, QueueStub as _QueueStub


def test_run_worker_process_dispatches_reset_pipeline_logs(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class FakeEngine:
        def __init__(self, **_kwargs) -> None:
            calls.append("init")

        def reset_pipeline_logs(self, _ui_state) -> None:
            calls.append("reset_pipeline_logs")

        def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = _QueueStub()
    run_worker_process(str(tmp_path), "reset_pipeline_logs", UiState().to_dict(), event_queue, _EventStub())

    assert calls == ["init", "reset_pipeline_logs", "close"]
    assert event_queue.items == [("done", None)]
