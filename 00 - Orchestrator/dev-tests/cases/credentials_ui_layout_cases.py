from __future__ import annotations

from orchestrator.ui import layout

from .credentials_ui_support import _make_app, install_fake_ctk


def test_layout_builds_status_credentials_log_tabs_in_order(monkeypatch, tmp_path) -> None:
    install_fake_ctk(monkeypatch)
    app = _make_app(tmp_path)

    layout.build_ui(app)

    assert app._tabs.tabs == ["Status", "Debug", "Credentials", "Models", "Log"]
    assert app._tabs.current == "Status"
    assert all(hasattr(app, name) for name in ("_start_btn", "_reset_btn", "_abort_btn", "_open_edit_suite_btn", "_status_help_btn", "_stage_labels", "_status_scroll_body"))
    assert all(not hasattr(app, name) for name in ("_debug_scroll_body", "_credentials_scroll_body", "_models_scroll_body", "_log_box"))

    app._tabs.set("Debug")
    app._tabs.set("Credentials")
    app._tabs.set("Models")
    app._tabs.set("Log")

    assert all(hasattr(app, name) for name in ("_debug_scroll_body", "_credentials_scroll_body", "_models_scroll_body", "_runtime_settings_widgets", "_log_box", "_debug_console_frame", "_debug_monitor_frame", "_debug_help_btn"))
    assert app._debug_results_tabs.tabs == ["Preview", "run.log", "Replay"]
    assert not hasattr(app, "_debug_artifacts_box")
