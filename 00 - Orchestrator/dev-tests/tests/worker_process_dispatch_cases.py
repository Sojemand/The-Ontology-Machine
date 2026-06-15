from __future__ import annotations

from pathlib import Path

from .worker_process_support import EventStub, QueueStub
from orchestrator.models import UiState
import orchestrator.worker as worker_module
from orchestrator.worker import run_worker_process


def test_run_worker_process_dispatches_activate_release_with_confirmation_payload(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []
    captured: dict[str, object] = {}

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

        def reset_pipeline_logs(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def activate_release(self, ui_state, *, confirmation_payload=None) -> None:
            captured["release_path"] = ui_state.semantic_release_path
            captured["confirmation_payload"] = confirmation_payload

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(
        str(tmp_path),
        "activate_release",
        {
            "ui_state": UiState(semantic_release_path="release.json").to_dict(),
            "activation_confirmation": {"decision": "activate_only"},
        },
        event_queue,
        EventStub(),
    )

    assert event_queue.items == [("done", None)]
    assert captured == {
        "release_path": "release.json",
        "confirmation_payload": {"decision": "activate_only"},
    }
    assert created[0].close_called is True


def test_run_worker_process_dispatches_create_database(monkeypatch, tmp_path: Path) -> None:
    created: list[object] = []
    captured: dict[str, object] = {}

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

        def reset_pipeline_logs(self, _ui_state) -> None:
            raise AssertionError("unexpected")

        def activate_release(self, _ui_state, *, confirmation_payload=None) -> None:
            raise AssertionError("unexpected")

        def create_database(self, ui_state, *, request) -> None:
            captured["selected_db"] = ui_state.selected_corpus_db_path
            captured["request"] = request

        def close(self) -> None:
            self.close_called = True

    monkeypatch.setattr(worker_module, "OrchestratorEngine", FakeEngine)

    event_queue = QueueStub()
    run_worker_process(
        str(tmp_path),
        "create_database",
        {
            "ui_state": UiState(selected_corpus_db_path="C:/db/new.db").to_dict(),
            "create_database": {"target_db_path": "C:/db/new.db", "bootstrap_mode": "no_release", "database_name": "new"},
        },
        event_queue,
        EventStub(),
    )

    assert event_queue.items == [("done", None)]
    assert captured == {
        "selected_db": "C:/db/new.db",
        "request": {"target_db_path": "C:/db/new.db", "bootstrap_mode": "no_release", "database_name": "new"},
    }
    assert created[0].close_called is True
