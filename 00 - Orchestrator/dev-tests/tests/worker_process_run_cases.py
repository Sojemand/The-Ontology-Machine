from __future__ import annotations

from pathlib import Path

from .worker_process_support import EventStub, QueueStub
from orchestrator.models import UiState
from orchestrator.pipeline import OrchestratorBusyError, OrchestratorCancelled
import orchestrator.worker as worker_module
from orchestrator.worker import run_worker_process


def test_run_worker_process_emits_done_and_closes_engine(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.snapshot_callback = kwargs["snapshot_callback"]
            self.log_callback = kwargs["log_callback"]
            self.close_called = False
            created.append(self)

        def run(self, _ui_state) -> None:
            self.snapshot_callback({"status": "running"})
            self.log_callback("hello")

        def run_embeddings(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def reset_run_history(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(str(tmp_path), "run", UiState().to_dict(), event_queue, EventStub())

    assert [kind for kind, _payload in event_queue.items] == ["snapshot", "log", "done"]
    assert created[0].close_called is True


def test_run_worker_process_emits_cancelled_and_closes_engine(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.close_called = False
            created.append(self)

        def run(self, _ui_state) -> None:
            raise OrchestratorCancelled()

        def run_embeddings(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def reset_run_history(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(str(tmp_path), "run", UiState().to_dict(), event_queue, EventStub())

    assert event_queue.items == [("cancelled", None)]
    assert created[0].close_called is True


def test_run_worker_process_surfaces_busy_error_and_closes_engine(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.close_called = False
            created.append(self)

        def run(self, _ui_state) -> None:
            raise OrchestratorBusyError("busy")

        def run_embeddings(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def reset_run_history(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(str(tmp_path), "run", UiState().to_dict(), event_queue, EventStub())

    assert event_queue.items == [("error", "busy")]
    assert created[0].close_called is True


def test_run_worker_process_surfaces_unknown_action_and_closes_engine(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []

    class FakeEngine:
        def __init__(self, **kwargs) -> None:
            self.close_called = False
            created.append(self)

        def run(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def run_embeddings(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def reset_run_history(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(str(tmp_path), "invalid", UiState().to_dict(), event_queue, EventStub())

    assert event_queue.items == [("error", "Unknown action: invalid")]
    assert created[0].close_called is True
