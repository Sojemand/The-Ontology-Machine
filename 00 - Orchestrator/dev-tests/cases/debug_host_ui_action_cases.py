from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.debug_host.types import DebugPlan, DebugStep
from orchestrator.ui import debug_rendering
from orchestrator.ui.debug_actions import DebugHostAppActions

from support.debug_host_ui_support_impl import make_app


def test_open_debug_artifacts_opens_session_root_not_only_outputs(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    session_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    app._debug_session = SimpleNamespace(session_root=session_root, output_root=output_root)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions_interactions.os.startfile",
        lambda target: captured.setdefault("target", target),
    )

    DebugHostAppActions._open_debug_artifacts(app)

    assert captured["target"] == session_root


def test_show_debug_help_opens_module_specific_info_window(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_module_var.set("optimizer")
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.debug_help.get_help",
        lambda module_key: ("Optimizer Debug Guide", f"body:{module_key}"),
    )
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.dialogs.show_info_window",
        lambda _app, *, title, body: captured.update({"title": title, "body": body}),
    )
    DebugHostAppActions._show_debug_help(app)
    assert captured == {"title": "Optimizer Debug Guide", "body": "body:optimizer"}


def test_optimizer_help_is_available_in_debug_host(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._input_entry.insert(0, str(tmp_path / "input"))
    app._debug_module_var.set("optimizer")
    app._debug_mode_var.set("single")
    app._debug_source_entry.insert(0, "docs/invoice.pdf")
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", _single_step_plan)

    debug_rendering.apply_view(app)

    assert app._debug_help_btn.config["state"] == "normal"

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.dialogs.show_info_window",
        lambda _app, *, title, body: captured.update({"title": title, "body": body}),
    )

    DebugHostAppActions._show_debug_help(app)

    assert captured["title"] == "Optimizer Debug Guide"
    assert "Optimizer" in captured["body"]
    assert "merged Optimizer" in captured["body"]
    assert "dispatches internally by profile" in captured["body"]


def test_corpus_builder_help_is_available_in_debug_host(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_module_var.set("corpus_builder")
    app._debug_mode_var.set("single")
    normalized_path = tmp_path / "normalized" / "invoice.structured.normalized.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text("{}", encoding="utf-8")
    app._debug_input_entry.insert(0, str(normalized_path))
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", _single_step_plan)

    debug_rendering.apply_view(app)

    assert app._debug_help_btn.config["state"] == "normal"

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.dialogs.show_info_window",
        lambda _app, *, title, body: captured.update({"title": title, "body": body}),
    )

    DebugHostAppActions._show_debug_help(app)

    assert captured["title"] == "Corpus Builder Debug Guide"
    assert "scan_debug_input" in captured["body"]
    assert "*.structured.normalized.json" in captured["body"]
    assert "outputs/corpus.db" in captured["body"]
    assert "Semantic Release" in captured["body"]
    assert "SQLite" in captured["body"]
    assert "Persist Page Images in DB" in captured["body"]
    assert "does not create embeddings" in captured["body"]


def _single_step_plan(module_key: str, mode: str, **_kwargs) -> DebugPlan:
    return DebugPlan(mode, (DebugStep.module(module_key, "debug_run"),))
