from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.debug_host.types import DebugPlan, DebugStep
from orchestrator.ui import debug_rendering

from .debug_host_ui_support import TextBox, make_app


def test_control_scope_skips_artifact_and_log_reload(monkeypatch, tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app._input_entry.insert(0, str(tmp_path / "input"))
    app._debug_log_box = TextBox()
    app._debug_session = SimpleNamespace(run_log_path=tmp_path / "run.log", active_step=None, result=None, snapshot=None)
    calls: list[str] = []

    monkeypatch.setattr(
        "orchestrator.ui.debug_rendering.plan_for",
        lambda module_key, _mode, **_kwargs: DebugPlan("single", (DebugStep.module(module_key, "debug_run"),)),
    )
    monkeypatch.setattr("orchestrator.ui.debug_rendering._apply_artifact_view", lambda *_args, **_kwargs: calls.append("artifacts"))
    monkeypatch.setattr("orchestrator.ui.debug_rendering.load_log", lambda _path: calls.append("log") or "run log")

    debug_rendering.apply_view(app, scope="controls")
    debug_rendering.apply_view(app, scope="full")

    assert calls == ["artifacts", "log"]
