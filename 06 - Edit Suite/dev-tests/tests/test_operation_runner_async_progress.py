from __future__ import annotations

from operation_runner_support import *  # noqa: F403

def test_run_surface_action_tracks_loading_until_async_delivery(monkeypatch) -> None:
    surface = _surface()
    app, _entry, events = _app(surface)
    captured = {}

    def fake_start(_app, *, work, deliver):
        captured["work"] = work
        captured["deliver"] = deliver

    monkeypatch.setattr(operation_runner.background_jobs, "start", fake_start)
    monkeypatch.setattr(
        operation_runner,
        "invoke_module_contract",
        lambda **_kwargs: {"status": "ok", "headline": "done", "summary_lines": ["ready"]},
    )

    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {"action": "verify_release_copy", "label": "Verify Release", "contract_module": "normalizer_vision.edit_contract"},
    )

    assert surface.surface_id in app._operation_action_loading
    assert events == []

    captured["deliver"](captured["work"](), None)

    assert surface.surface_id not in app._operation_action_loading
    assert events == ["render"]
    assert operation_runner.result_text(app, surface.surface_id) == "Verify Release: ok\ndone\nready"

def test_long_running_action_updates_progress_window(monkeypatch) -> None:
    surface = SurfaceModel(
        surface_id="corpus_builder.settings::action::rebuild_from_artifacts",
        label="Rebuild Corpus",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={"action_buttons": [{"action": "rebuild_from_artifacts"}]},
        value={},
        draft={},
        operation_links=(),
    )
    app, _entry, _events = _app(surface)
    pending = {}
    progress_handle = object()
    progress_events = {}

    def fake_start(_app, *, work, deliver):
        pending["work"] = work
        pending["deliver"] = deliver

    def fake_progress_start(progress_app, surface_id, action_link, payload):
        progress_events["start"] = (progress_app, surface_id, action_link, payload)
        return progress_handle

    def fake_progress_finish(handle, response, error):
        progress_events["finish"] = (handle, response, error)

    monkeypatch.setattr(operation_runner.background_jobs, "start", fake_start)
    monkeypatch.setattr(operation_runner.operation_progress, "start", fake_progress_start)
    monkeypatch.setattr(operation_runner.operation_progress, "finish", fake_progress_finish)
    monkeypatch.setattr(operation_runner, "invoke_module_contract", lambda **_kwargs: {"status": "ok", "headline": "Rebuild completed"})

    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "rebuild_from_artifacts",
            "label": "Rebuild Corpus",
            "contract_module": "corpus_builder.orchestrator_contract",
            "show_progress_dialog": True,
            "progress_warning": "Nach dem Rebuild fehlen Embeddings.",
        },
    )

    assert progress_events["start"][1] == surface.surface_id
    assert progress_events["start"][3]["action"] == "rebuild_from_artifacts"

    pending["deliver"](pending["work"](), None)

    assert progress_events["finish"][0] is progress_handle
    assert progress_events["finish"][1]["headline"] == "Rebuild completed"
    assert progress_events["finish"][2] is None

def test_result_text_formats_hint_fields_and_artifacts() -> None:
    surface = _surface()
    app, _entry, _events = _app(surface)
    app._operation_results[surface.surface_id] = {
        "label": "Apply Verified Release Copy",
        "response": {
            "status": "ok",
            "headline": "Verified release copy applied",
            "summary_lines": ["Release: rel.v1"],
            "required_fields": ["release_path", "corpus_db_path"],
            "allowed_values": ["de"],
            "references_existing_codes": ["finance.default.v1"],
            "validation_risks": ["reference_drift"],
            "compile_effect": "Compiled compatibility assets refreshed.",
            "prompt_effect": "Prompt context updated after export.",
            "corpus_effect": "Corpus Builder activation applied.",
            "artifacts": [{"label": "Export", "value": "C:/exports/release.json"}],
        },
    }

    assert operation_runner.result_text(app, surface.surface_id) == (
        "Apply Verified Release Copy: ok\n"
        "Verified release copy applied\n"
        "Release: rel.v1\n"
        "Required fields: release_path, corpus_db_path\n"
        "Allowed values: de\n"
        "Existing refs: finance.default.v1\n"
        "Validation risks: reference_drift\n"
        "Compile: Compiled compatibility assets refreshed.\n"
        "Prompt: Prompt context updated after export.\n"
        "Corpus: Corpus Builder activation applied.\n"
        "Export: C:/exports/release.json"
    )

def test_finish_surface_action_ignores_stale_operation_results() -> None:
    surface = _surface()
    app, _entry, events = _app(surface)
    app._operation_action_loading = {surface.surface_id}
    app._request_tokens = {f"operation:{surface.surface_id}": 2}

    operation_runner._finish_surface_action(
        app,
        surface.surface_id,
        {"action": "verify_release_copy", "label": "Verify Release", "contract_module": "normalizer_vision.edit_contract"},
        f"operation:{surface.surface_id}",
        1,
        {"status": "ok"},
        None,
    )

    assert app._operation_results == {}
    assert app._operation_action_loading == {surface.surface_id}
    assert events == []
