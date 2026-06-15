from __future__ import annotations

from operation_runner_support import *  # noqa: F403

def test_run_surface_action_merges_fixed_button_payload(monkeypatch) -> None:
    surface = SurfaceModel(
        surface_id="mcp_server.support_monitor",
        label="Support Monitor",
        kind="capability_summary",
        editable=False,
        editor_kind="support_monitor",
        descriptor={},
        value={},
        draft={},
        operation_links=(),
    )
    app, _entry, events = _app(surface)
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "queued", "queued_path": "C:/support/outbox/report.queued.json"}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "support_incident_workflow",
            "label": "Queue Report",
            "contract_module": "mcp_server.edit_contract",
            "fixed_payload": {"workflow_action": "queue", "assessment_id": "assessment-123", "user_confirmed": True},
        },
    )

    assert events == ["render"]
    assert captured["payload"] == {
        "action": "support_incident_workflow",
        "workflow_action": "queue",
        "assessment_id": "assessment-123",
        "user_confirmed": True,
    }
    assert "report.queued.json" in operation_runner.result_text(app, surface.surface_id)

def test_run_surface_action_reads_release_apply_paths(monkeypatch) -> None:
    surface = _surface()
    app, entry, events = _app(surface)
    app._action_widgets[surface.surface_id]["editor"] = SimpleNamespace(
        _action_inputs={
            "release_path": {
                "spec": {"name": "release_path", "persist_key": "release_path", "required": True},
                "kind": "open_file",
                "widget": _Entry("C:/exports/release.json"),
            },
            "corpus_db_path": {
                "spec": {"name": "corpus_db_path", "persist_key": "corpus_db_path", "required": True},
                "kind": "open_file",
                "widget": _Entry("C:/corpus/output/corpus.db"),
            },
        }
    )
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "ok", "headline": "done", "summary_lines": ["activated"]}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "apply_verified_release_copy",
            "label": "Apply Verified Release Copy",
            "contract_module": "corpus_builder.orchestrator_contract",
            "inputs": [
                {"name": "release_path", "field_type": "open_file", "required": True},
                {"name": "corpus_db_path", "field_type": "open_file", "required": True},
            ],
        },
    )

    assert events == ["render"]
    assert captured["payload"] == {
        "action": "apply_verified_release_copy",
        "release_path": "C:/exports/release.json",
        "corpus_db_path": "C:/corpus/output/corpus.db",
    }
    assert app._ui_state["operation_contexts"][entry.slot_name]["release_path"] == "C:/exports/release.json"
    assert app._ui_state["operation_contexts"][entry.slot_name]["corpus_db_path"] == "C:/corpus/output/corpus.db"

def test_run_surface_action_reads_new_corpus_db_dialog_payload(monkeypatch) -> None:
    surface = _surface()
    app, entry, events = _app(surface)
    app._action_widgets[surface.surface_id]["editor"] = SimpleNamespace(
        _action_inputs={
            "release_path": {
                "spec": {"name": "release_path", "persist_key": "release_path", "required": True},
                "kind": "save_file",
                "widget": _Entry("C:/exports/release.json"),
            }
        }
    )
    monkeypatch.setattr(
        operation_runner,
        "prompt_new_corpus_db_creation",
        lambda *_args, **_kwargs: {"confirmation_artifact_path": "C:/state/corpus-confirmation.json"},
    )
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "ok", "headline": "done", "summary_lines": ["created"]}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "materialize_corpus_db_from_release",
            "label": "Materialize Corpus DB",
            "contract_module": "corpus_builder.orchestrator_contract",
            "inputs": [
                {"name": "release_path", "field_type": "save_file", "required": True},
            ],
            "new_corpus_db_dialog": {
                "label_name": "database_label",
                "locale_name": "taxonomy_locale",
            },
        },
    )

    assert events == ["render"]
    assert captured["payload"] == {
        "action": "materialize_corpus_db_from_release",
        "release_path": "C:/exports/release.json",
        "confirmation_artifact_path": "C:/state/corpus-confirmation.json",
    }
    assert app._ui_state["operation_contexts"][entry.slot_name]["release_path"] == "C:/exports/release.json"

def test_prompt_new_corpus_db_creation_rejects_headless_bypass() -> None:
    surface = _surface()
    app, _entry, _events = _app(surface)
    app._ui_state["operation_contexts"][app._selected_module] = {}
    action_link = {
        "action": "materialize_corpus_db_from_release",
        "new_corpus_db_dialog": {
            "label_persist_key": "new_corpus_db_label",
            "locale_persist_key": "new_corpus_db_taxonomy_locale",
        },
    }
    app._ui_state["operation_contexts"][app._selected_module]["new_corpus_db_label"] = "Bereits gesetzt"
    app._ui_state["operation_contexts"][app._selected_module]["new_corpus_db_taxonomy_locale"] = "de"

    try:
        prompt_new_corpus_db_creation(app, surface.surface_id, action_link, {})
    except ValueError as exc:
        assert "interactive UI dialog" in str(exc)
    else:
        raise AssertionError("Headless new corpus DB creation must fail closed.")
