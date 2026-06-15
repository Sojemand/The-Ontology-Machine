from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

main_module = importlib.import_module("orchestrator.main")
surface_module = importlib.import_module("orchestrator.ui.surface")


def test_main_defaults_to_gui_surface(monkeypatch) -> None:
    events: list[str] = []

    class FakeApp:
        def mainloop(self) -> None:
            events.append("mainloop")

    monkeypatch.setattr(main_module, "_setup_logging", lambda: events.append("logging"))
    monkeypatch.setattr(main_module, "ensure_startup_prerequisites", lambda: events.append("prereqs"))
    monkeypatch.setattr(main_module, "_load_app_class", lambda: FakeApp)

    main_module.main([])

    assert events == ["logging", "prereqs", "mainloop"]


def test_main_surfaces_startup_error_as_system_exit(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "_setup_logging", lambda: None)
    monkeypatch.setattr(
        main_module,
        "ensure_startup_prerequisites",
        lambda: (_ for _ in ()).throw(main_module.StartupPrerequisiteError("broken runtime")),
    )

    with pytest.raises(SystemExit, match="broken runtime"):
        main_module.main([])


def test_report_callback_exception_surfaces_message_and_logs(monkeypatch, caplog) -> None:
    shown_messages: list[str] = []
    appended_logs: list[str] = []
    monkeypatch.setattr(surface_module.dialogs, "show_error", lambda message: shown_messages.append(message))

    app = SimpleNamespace(_append_log=lambda message: appended_logs.append(message))
    exc = RuntimeError
    val = RuntimeError("boom")

    with caplog.at_level("ERROR"):
        surface_module.OrchestratorApp.report_callback_exception(app, exc, val, None)

    assert "Tkinter callback failed" in caplog.text
    assert appended_logs == ["[ERROR] UI callback failed: boom"]
    assert shown_messages == ["boom\n\nDetails are available in state/orchestrator.log."]
