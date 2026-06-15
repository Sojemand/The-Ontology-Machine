from __future__ import annotations

from operation_runner_support import *  # noqa: F403
from edit_suite import validation

def test_run_surface_action_blocks_dirty_drafts() -> None:
    surface = _surface()
    app, entry, events = _app(surface)
    app._drafts[entry.slot_name]["normalizer.taxonomy_release_draft"] = DraftState("normalizer.taxonomy_release_draft", {"release": {}}, dirty=True)

    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {"action": "build_runtime_semantic_assets", "label": "Build Runtime Assets", "contract_module": "normalizer_vision.orchestrator_contract", "requires_saved_surface": True},
    )

    assert events == ["render"]
    assert "Unsaved changes" in operation_runner.result_text(app, surface.surface_id)

def test_run_surface_action_passes_output_path_and_formats_result(monkeypatch) -> None:
    surface = _surface()
    app, _entry, events = _app(surface)
    captured = {}
    monkeypatch.setattr(operation_runner.fd, "asksaveasfilename", lambda **_kwargs: "C:/exports/release.json")

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "OK", "output_path": payload["output_path"], "message": "created", "release_id": "rel.v2"}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {"action": "publish_semantic_release", "label": "Publish Semantic Release", "contract_module": "normalizer_vision.orchestrator_contract", "requires_output_path": True},
    )

    assert events == ["render"]
    assert captured["payload"] == {"action": "publish_semantic_release", "output_path": str(Path("C:/exports/release.json"))}
    assert operation_runner.result_text(app, surface.surface_id) == (
        f"Publish Semantic Release: ok\n"
        f"{Path('C:/exports/release.json')}\n"
        "created\n"
        "{\n  \"release_id\": \"rel.v2\"\n}"
    )

def test_suggested_output_name_sanitizes_release_id() -> None:
    surface = _surface("semantic/release current")
    app, _entry, _events = _app(surface)

    assert operation_runner.suggested_output_name(app, surface.surface_id) == "semantic.release_current.json"

def test_suggested_output_name_caps_long_release_id() -> None:
    surface = _surface("semantic/" + "very-long-release-" * 12)
    app, _entry, _events = _app(surface)
    name = operation_runner.suggested_output_name(app, surface.surface_id)

    assert len(name) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert name.endswith(".json")

def test_run_surface_action_reads_structured_action_inputs(monkeypatch) -> None:
    surface = SurfaceModel(
        surface_id="corpus_builder.search_policy::action::search",
        label="Search Corpus",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={"action_buttons": [{"action": "search"}]},
        value={},
        draft={},
        operation_links=(),
    )
    app, entry, events = _app(surface)
    app._action_widgets[surface.surface_id]["editor"] = SimpleNamespace(
        _action_inputs={
            "query": {"spec": {"name": "query", "persist_key": "query"}, "kind": "text", "widget": _Entry("invoice")},
            "mode": {"spec": {"name": "mode", "persist_key": "search_mode"}, "kind": "select", "variable": _Entry("Hybrid"), "widget": None},
            "goal": {"spec": {"name": "goal", "persist_key": "bootstrap_goal"}, "kind": "multiline_text", "widget": _TextBox("erste zeile\nzweite zeile\n")},
        }
    )
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "ok", "headline": "done", "summary_lines": ["Hits: 1"], "detail": {"rows": 1}}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {"action": "search", "label": "Search Corpus", "contract_module": "corpus_builder.orchestrator_contract"},
    )

    assert events == ["render"]
    assert captured["payload"] == {"action": "search", "query": "invoice", "mode": "Hybrid", "goal": "erste zeile\nzweite zeile"}
    assert app._ui_state["operation_contexts"][entry.slot_name]["search_mode"] == "Hybrid"
    assert app._ui_state["operation_contexts"][entry.slot_name]["bootstrap_goal"] == "erste zeile\nzweite zeile"
