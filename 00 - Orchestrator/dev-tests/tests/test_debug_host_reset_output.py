from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.debug_host import clear_sessions
from orchestrator.debug_host.types import DebugResult
from orchestrator.ui import debug_rendering
from orchestrator.ui.debug_actions import DebugHostAppActions

from .debug_host_ui_support import Widget, make_app


def test_reset_debug_output_clears_sessions_and_preserves_debug_state(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_reset_output_btn = Widget()
    app._debug_state_path.parent.mkdir(parents=True, exist_ok=True)
    app._debug_state_path.write_text('{"module_key":"optimizer","mode":"scan"}', encoding="utf-8")
    session_root = _write_session(app._state_dir, "dbg_alpha", "interpreter")
    app._debug_session = _session(session_root, status="ok")
    app._selected_debug_artifact_index = 3
    applied: list[str] = []

    monkeypatch.setattr("orchestrator.ui.debug_actions.dialogs.confirm_reset_debug_output", lambda _app: True)
    monkeypatch.setattr("orchestrator.ui.debug_actions.debug_rendering.apply_view", lambda _app: applied.append("applied"))

    DebugHostAppActions._reset_debug_output(app)

    assert applied == ["applied"]
    assert app._debug_session is None
    assert app._selected_debug_artifact_index == 0
    assert not (app._state_dir / "debug_sessions").exists()
    assert app._debug_state_path.read_text(encoding="utf-8") == '{"module_key":"optimizer","mode":"scan"}'


def test_reset_debug_output_respects_cancelled_confirmation(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_reset_output_btn = Widget()
    session_root = _write_session(app._state_dir, "dbg_alpha", "interpreter")
    current_session = _session(session_root, status="ok")
    app._debug_session = current_session

    monkeypatch.setattr("orchestrator.ui.debug_actions.dialogs.confirm_reset_debug_output", lambda _app: False)
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.debug_host.clear_sessions",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("clear_sessions should not run")),
    )
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.debug_rendering.apply_view",
        lambda _app: (_ for _ in ()).throw(AssertionError("apply_view should not run")),
    )

    DebugHostAppActions._reset_debug_output(app)

    assert app._debug_session is current_session
    assert (app._state_dir / "debug_sessions").exists()


def test_update_buttons_disables_reset_while_running_and_when_empty(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app._debug_reset_output_btn = Widget()
    _write_session(app._state_dir, "dbg_alpha", "interpreter")

    debug_rendering.update_buttons(app)
    assert app._debug_reset_output_btn.config["state"] == "normal"

    app._debug_session = SimpleNamespace(active_step="debug_run", result=None)
    debug_rendering.update_buttons(app)
    assert app._debug_reset_output_btn.config["state"] == "disabled"

    app._debug_session = None
    clear_sessions(state_root=app._state_dir)
    debug_rendering.update_buttons(app)
    assert app._debug_reset_output_btn.config["state"] == "disabled"


def test_debug_session_poll_marks_finished_session_and_enables_reset(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_reset_output_btn = Widget()
    session_root = _write_session(app._state_dir, "dbg_alpha", "interpreter")
    app._debug_session = SimpleNamespace(
        active_step="debug_run",
        result=None,
        snapshot=None,
        session_root=session_root,
        output_root=session_root / "outputs",
        run_log_path=session_root / "run.log",
    )

    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.debug_host.refresh",
        lambda _session, modules: SimpleNamespace(
            active_step=None,
            result=DebugResult(status="ok", summary="done"),
            snapshot=None,
            session_root=session_root,
            output_root=session_root / "outputs",
            run_log_path=session_root / "run.log",
        ),
    )
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.debug_rendering.apply_view",
        lambda _app, scope="full": debug_rendering.update_buttons(_app),
    )

    DebugHostAppActions._schedule_debug_session_poll(app)

    handle = app._debug_session_poll_handle
    assert handle is not None

    app._run_after(handle)

    assert app._debug_session.result.status == "ok"
    assert app._debug_session.active_step is None
    assert app._debug_session_poll_handle is None
    assert app._debug_reset_output_btn.config["state"] == "normal"


def _session(session_root: Path, *, status: str):
    return SimpleNamespace(
        active_step=None,
        session_root=session_root,
        output_root=session_root / "outputs",
        run_log_path=session_root / "run.log",
        snapshot=None,
        result=DebugResult(status=status, summary=status),
    )


def _write_session(state_root: Path, session_id: str, module_key: str) -> Path:
    session_root = state_root / "debug_sessions" / session_id / module_key
    (session_root / "outputs").mkdir(parents=True, exist_ok=True)
    (session_root / "run.log").write_text("started\n", encoding="utf-8")
    return session_root

