from __future__ import annotations

from pathlib import Path

from orchestrator.debug_host.types import DebugPlan, DebugStep
from orchestrator.ui import debug_rendering, debug_repository
from orchestrator.ui.debug_actions import DebugHostAppActions

from .debug_host_ui_support import make_app


def test_dismiss_debug_artifact_hides_loaded_import_from_view(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    artifact = tmp_path / "replay" / "invoice.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"file_name":"invoice.pdf"}', encoding="utf-8")
    app._debug_artifact_import_entry.insert(0, str(artifact))
    monkeypatch.setattr(
        "orchestrator.ui.debug_rendering.plan_for",
        lambda module_key, mode, **_kwargs: DebugPlan(mode, (DebugStep.module(module_key, "debug_run"),)),
    )

    debug_rendering.apply_view(app)

    assert len(app._debug_artifact_entries) == 1
    assert app._debug_artifact_summary_label.value == "1 artifacts loaded"

    DebugHostAppActions._dismiss_debug_artifact(app, artifact)

    assert len(app._debug_artifact_entries) == 0
    assert str(artifact) not in app._hidden_debug_artifact_paths
    assert app._debug_artifact_import_entry.value == ""
    assert app._debug_artifact_summary_label.value == "No artifacts loaded."
    assert app._debug_preview_box.value == ""
    assert app._debug_replay_status_label.value == "No replay loaded."


def test_replay_import_does_not_return_after_debug_host_reload(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    artifact = tmp_path / "replay" / "invoice.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"file_name":"invoice.pdf"}', encoding="utf-8")
    app._debug_artifact_import_entry.insert(0, str(artifact))
    monkeypatch.setattr(
        "orchestrator.ui.debug_rendering.plan_for",
        lambda module_key, mode, **_kwargs: DebugPlan(mode, (DebugStep.module(module_key, "debug_run"),)),
    )

    debug_rendering.apply_view(app)
    DebugHostAppActions._dismiss_debug_artifact(app, artifact)

    reloaded = make_app(tmp_path)
    debug_repository.restore_state(reloaded)
    debug_rendering.apply_view(reloaded)

    assert reloaded._debug_artifact_import_entry.value == ""
    assert len(reloaded._debug_artifact_entries) == 0
    assert reloaded._debug_artifact_summary_label.value == "No artifacts loaded."
    assert reloaded._debug_replay_status_label.value == "No replay loaded."
