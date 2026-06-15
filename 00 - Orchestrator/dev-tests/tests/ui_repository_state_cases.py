from __future__ import annotations

import json

from orchestrator.state import load_ui_state
from orchestrator.ui import repository

from .ui_repository_support import _make_app


def test_save_and_restore_ui_state_roundtrip(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._input_entry.insert(0, "input")
    app._artifact_entry.insert(0, "artifacts")
    app._release_entry.insert(0, "release.json")
    app._corpus_entry.insert(0, "corpus")
    app._selected_db_entry.insert(0, "corpus\\selected.db")
    app._semantic_release_mode_var.set("Override Release")
    app._mode_var.set("single")

    repository.save_ui_state(app)

    payload = json.loads(app._ui_state_path.read_text(encoding="utf-8"))

    loaded = load_ui_state(app._ui_state_path)
    restored = _make_app(tmp_path, state=loaded)
    repository.restore_ui_state(restored)

    assert repository.current_ui_state(restored) == loaded
    assert "auth_mode" not in payload
    assert "oauth_session" not in payload


def test_set_entry_path_updates_entry_and_triggers_change_hook(tmp_path) -> None:
    calls: list[str] = []
    app = _make_app(tmp_path)
    app._on_ui_change = lambda: calls.append("changed")

    repository.set_entry_path(app, app._input_entry, "")
    repository.set_entry_path(app, app._input_entry, "C:/input")

    assert app._input_entry.get() == "C:/input"
    assert calls == ["changed"]
