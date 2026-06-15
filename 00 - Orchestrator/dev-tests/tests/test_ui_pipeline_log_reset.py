from __future__ import annotations

from types import SimpleNamespace

from orchestrator.models import UiState
from orchestrator.ui import credentials_layout, debug_controls_layout, debug_layout, debug_monitor_layout, debug_results_layout, layout, model_settings_layout, responsive, status_control_cards, status_layout, workflow
from tests.test_credentials_ui import _fake_ctk, _make_app


def _patch_layout_ctk(monkeypatch) -> None:
    fake_ctk = _fake_ctk()
    for module in (layout, status_layout, status_control_cards, credentials_layout, debug_layout, debug_controls_layout, debug_monitor_layout, debug_results_layout, model_settings_layout, responsive):
        monkeypatch.setattr(module, "ctk", fake_ctk)


class _Widget:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs) -> None:
        self.config.update(kwargs)


class _Context:
    def Queue(self):
        return object()

    def Event(self):
        return object()

    def Process(self, **_kwargs):
        return SimpleNamespace(start=lambda: None)


def test_status_layout_builds_reset_pipeline_logs_button(monkeypatch, tmp_path) -> None:
    _patch_layout_ctk(monkeypatch)
    app = _make_app(tmp_path)

    layout.build_ui(app)

    assert hasattr(app, "_create_artifact_tree_btn")
    assert app._create_artifact_tree_btn.cget("text") == "Create Artifact Tree"
    assert hasattr(app, "_reset_pipeline_logs_btn")
    assert app._reset_pipeline_logs_btn.cget("text") == "Reset Pipeline Logs"


def test_reset_pipeline_logs_requires_confirmation(monkeypatch, tmp_path) -> None:
    started: list[str] = []
    app = SimpleNamespace(_processing=False, _state_dir=tmp_path / "state", _flush_pending_saves=lambda: None, _save_ui_state=lambda: None, _clear_log=lambda: None, _current_ui_state=lambda: UiState(), _start_worker=lambda **_kwargs: started.append("start"), _append_log=lambda _line: None)
    monkeypatch.setattr("orchestrator.ui.workflow.dialogs.confirm_reset_pipeline_logs", lambda _app: False)

    workflow.reset_pipeline_logs(app)

    assert started == []


def test_reset_pipeline_logs_clears_logs_and_dispatches_worker(monkeypatch, tmp_path) -> None:
    events: list[object] = []
    app = SimpleNamespace(_processing=False, _state_dir=tmp_path / "state", _flush_pending_saves=lambda: events.append("flush"), _save_ui_state=lambda: events.append("save"), _clear_log=lambda: events.append("clear"), _current_ui_state=lambda: UiState(input_folder="in"), _start_worker=lambda **kwargs: events.append(kwargs), _append_log=lambda _line: None)
    monkeypatch.setattr("orchestrator.ui.workflow.dialogs.confirm_reset_pipeline_logs", lambda _app: True)
    monkeypatch.setattr("orchestrator.ui.workflow.reset_logging_files", lambda _state_dir: events.append("reset_logs"))

    workflow.reset_pipeline_logs(app)

    assert events == ["flush", "save", "clear", "reset_logs", {"action": "reset_pipeline_logs", "ui_state": UiState(input_folder="in")}]


def test_start_and_finish_worker_toggle_reset_pipeline_logs_button(monkeypatch, tmp_path) -> None:
    scheduled: list[str] = []
    app = SimpleNamespace(_project_root=tmp_path, _processing=False, _stop_requested=False, _active_action="", _snapshot=None, _mp_context=_Context(), _worker_process=None, _worker_queue=None, _worker_cancel_event=None, _cleanup_worker_resources=lambda: None, _apply_snapshot=lambda _snapshot: None, _update_button_state=lambda: None, _start_btn=_Widget(), _reset_btn=_Widget(), _reset_pipeline_logs_btn=_Widget(), _abort_btn=_Widget(), _wait_for_worker_exit=lambda: None)
    monkeypatch.setattr("orchestrator.ui.workflow.queue_scheduler.schedule", lambda _app: scheduled.append("schedule"))
    monkeypatch.setattr("orchestrator.ui.workflow.queue_scheduler.stop", lambda _app: scheduled.append("stop"))

    workflow.start_worker(app, action="reset_pipeline_logs", ui_state=UiState())

    assert app._reset_pipeline_logs_btn.config["state"] == "disabled"
    assert app._reset_pipeline_logs_btn.config["text"] == "Reset Pipeline Logs..."

    workflow.finish_worker(app)

    assert app._reset_pipeline_logs_btn.config["state"] == "normal"
    assert app._reset_pipeline_logs_btn.config["text"] == "Reset Pipeline Logs"
    assert scheduled == ["schedule", "stop"]
