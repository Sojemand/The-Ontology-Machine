from __future__ import annotations

from types import SimpleNamespace

import pytest

from orchestrator.models import PipelineSnapshot, StageSnapshot, UiState
from orchestrator.ui import OrchestratorApp
from orchestrator.ui.surface_actions import OrchestratorAppActions
from orchestrator.ui import theme


class _FakeQueue:
    def __init__(self) -> None:
        self.closed = False
        self.joined = False

    def close(self) -> None:
        self.closed = True

    def join_thread(self) -> None:
        self.joined = True


class _FakeProcess:
    def __init__(self, start_error: Exception | None = None) -> None:
        self._start_error = start_error
        self.closed = False
        self.started = False

    def start(self) -> None:
        if self._start_error is not None:
            raise self._start_error
        self.started = True

    def close(self) -> None:
        self.closed = True


class _FailingContext:
    def __init__(self, fail_at: str) -> None:
        self.fail_at = fail_at
        self.queue: _FakeQueue | None = None
        self.process: _FakeProcess | None = None

    def Queue(self):
        if self.fail_at == "queue":
            raise PermissionError("queue blocked")
        self.queue = _FakeQueue()
        return self.queue

    def Event(self):
        if self.fail_at == "event":
            raise RuntimeError("event blocked")
        return object()

    def Process(self, **_kwargs):
        start_error = RuntimeError("start blocked") if self.fail_at == "start" else None
        self.process = _FakeProcess(start_error=start_error)
        return self.process


class _FakeProgressBar:
    def __init__(self) -> None:
        self.value = 0.0

    def set(self, value: float) -> None:
        self.value = value


class _FakeLabel:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs) -> None:
        self.config.update(kwargs)


def test_start_worker_rolls_back_state_when_worker_bootstrap_fails(tmp_path) -> None:
    ui_state = UiState(
        input_folder="input",
        artifact_folder="artifacts",
        corpus_output_folder="corpus",
    )

    for fail_at, expected_message in (
        ("queue", "queue blocked"),
        ("event", "event blocked"),
        ("start", "start blocked"),
    ):
        applied: list[tuple[bool, bool]] = []
        updated: list[str] = []
        cleaned: list[str] = []
        context = _FailingContext(fail_at)
        app = SimpleNamespace(
            _project_root=tmp_path,
            _processing=False,
            _stop_requested=True,
            _active_action="",
            _snapshot=PipelineSnapshot(),
            _mp_context=context,
            _worker_process=None,
            _worker_queue=None,
            _worker_cancel_event=None,
        )
        app._cleanup_worker_resources = lambda: cleaned.append("cleanup")
        app._apply_snapshot = lambda snapshot: applied.append((snapshot.is_running, snapshot.aborted))
        app._update_button_state = lambda: updated.append("update")

        with pytest.raises(Exception, match=expected_message):
            OrchestratorApp._start_worker(app, action="run", ui_state=ui_state)

        assert cleaned == ["cleanup"]
        assert applied[0] == (True, False)
        assert applied[-1] == (False, False)
        assert updated == ["update"]
        assert app._processing is False
        assert app._stop_requested is False
        assert app._active_action == ""
        assert app._worker_process is None
        assert app._worker_queue is None
        assert app._worker_cancel_event is None
        assert app._snapshot.is_running is False
        if context.queue is not None:
            assert context.queue.closed is True
            assert context.queue.joined is True
        if context.process is not None:
            assert context.process.closed is True


def test_apply_snapshot_updates_progress_and_status_colors() -> None:
    snapshot = PipelineSnapshot(
        total=4,
        completed=2,
        pending=1,
        success=1,
        errors=1,
        needs_review=0,
        retries=2,
        current_file="doc.pdf",
        current_attempt=2,
        current_route_family="Documents",
        current_optimizer_module="Optimizer",
        current_interpreter_module="Interpreter",
        current_intake_reason="Born-digital PDF detected.",
        stage_statuses={
            "Intake": StageSnapshot(status=theme.STATUS_DONE, detail="Documents | Optimizer | Interpreter | Born-digital PDF detected."),
            "Runtime Semantics": StageSnapshot(status=theme.STATUS_DONE, detail="semantic_release.default | 1 | sha256:semantic"),
            "Optimizer": StageSnapshot(status=theme.STATUS_DONE, detail="Documents | Optimizer | raw.json"),
            "Request Enrichment": StageSnapshot(status=theme.STATUS_DONE, detail="interpreter.request.json"),
            "Interpreter": StageSnapshot(status="Review", detail="manual check", progress_current=2, progress_total=3, progress_label="Requests"),
            "Validator": StageSnapshot(status=theme.STATUS_ERROR, detail="schema"),
            "Normalizer": StageSnapshot(status=theme.STATUS_READY, detail="", progress_current=1, progress_total=3, progress_label="Requests"),
            "Corpus Builder": StageSnapshot(status="loaded", detail="corpus.db"),
            "Embeddings": StageSnapshot(status="Processing...", detail="corpus.db"),
        },
    )
    app = SimpleNamespace(
        _progress=_FakeProgressBar(),
        _status_label=_FakeLabel(),
        _counter_labels={name: _FakeLabel() for name in ["Pending", "Success", "Errors", "Needs Review", "Retries"]},
        _route_labels={name: _FakeLabel() for name in ["Route Family", "Optimizer", "Interpreter", "Intake Reason"]},
        _stage_labels={name: (_FakeLabel(), _FakeLabel(), _FakeLabel()) for name in snapshot.stage_statuses},
    )

    OrchestratorApp._apply_snapshot(app, snapshot)

    assert app._progress.value == 0.5
    assert app._status_label.config["text"] == "2/4 completed | File: doc.pdf | Attempt: 2"
    assert app._status_label.config["text_color"] == theme.COLOR_ERROR
    assert app._counter_labels["Retries"].config["text"] == "2"
    assert app._route_labels["Route Family"].config["text"] == "Documents"
    assert app._route_labels["Optimizer"].config["text"] == "Optimizer"
    assert app._stage_labels["Optimizer"][0].config["text_color"] == theme.COLOR_SUCCESS
    assert app._stage_labels["Interpreter"][0].config["text_color"] == theme.COLOR_WARNING
    assert app._stage_labels["Interpreter"][2].config["text"] == "2/3 Requests"
    assert app._stage_labels["Normalizer"][2].config["text"] == "1/3 Requests"
    assert app._stage_labels["Validator"][0].config["text_color"] == theme.COLOR_ERROR
    assert app._stage_labels["Normalizer"][0].config["text_color"] == theme.COLOR_TEXT


def test_initialize_model_settings_tab_restores_runtime_settings_and_rerenders_catalog(monkeypatch) -> None:
    calls: list[str] = []
    app = SimpleNamespace(
        _runtime_settings_widgets={"interpreter": {}},
        _restore_runtime_settings=lambda: calls.append("restore"),
    )
    monkeypatch.setattr("orchestrator.ui.surface_actions.model_catalog_actions.render_model_catalog", lambda _app: calls.append("render"))

    OrchestratorAppActions._initialize_model_settings_tab(app)

    assert calls == ["restore", "render"]

