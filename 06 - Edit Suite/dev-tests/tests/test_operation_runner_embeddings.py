from __future__ import annotations

from operation_runner_support import *  # noqa: F403

def test_generate_embeddings_routes_through_orchestrator(monkeypatch, tmp_path: Path) -> None:
    corpus_builder_root = tmp_path / "05 - Corpus Builder"
    corpus_builder_root.mkdir()
    orchestrator_root = tmp_path / "00 - Orchestrator"
    (orchestrator_root / "state").mkdir(parents=True)
    (orchestrator_root / "module-manifest.json").write_text("{}", encoding="utf-8")
    input_root = tmp_path / "input"
    input_root.mkdir()
    artifact_root = tmp_path / "artefacts"
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db_path = corpus_root / "corpus.db"
    corpus_db_path.write_bytes(b"")
    (orchestrator_root / "state" / "ui_state.json").write_text(
        json.dumps(
            {
                "input_folder": str(input_root),
                "artifact_folder": str(artifact_root),
                "corpus_output_folder": str(corpus_root),
                "selected_corpus_db_path": str(corpus_db_path),
                "mode": "batch",
            }
        ),
        encoding="utf-8",
    )
    corpus_entry = _entry(
        slot_name="05 - Corpus Builder",
        display_name="Corpus Builder",
        module_root=str(corpus_builder_root),
        module_key="corpus_builder",
        edit_contract_path="corpus_builder/edit_contract",
    )
    orchestrator_entry = _entry(
        slot_name="00 - Orchestrator",
        display_name="Orchestrator",
        module_root=str(orchestrator_root),
        module_key="orchestrator",
        edit_contract_path="orchestrator/edit_contract",
    )
    surface = SurfaceModel(
        surface_id="corpus_builder.embeddings_policy::action::generate_embeddings",
        label="Generate Embeddings",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={"action_buttons": [{"action": "generate_embeddings"}]},
        value={},
        draft={},
        operation_links=(),
    )
    events: list[str] = []
    app = SimpleNamespace(
        _pipeline_root=tmp_path,
        _state_root=tmp_path / "edit-suite-state",
        _snapshot=SimpleNamespace(entries=(orchestrator_entry, corpus_entry)),
        _ui_state={"operation_contexts": {}},
        _selected_module=corpus_entry.slot_name,
        _drafts={corpus_entry.slot_name: {}},
        _action_widgets={surface.surface_id: {"surface": surface}},
        _operation_results={},
        _render_detail_only=False,
        _selected_entry=lambda: corpus_entry,
        _render=lambda: events.append("render"),
    )
    app._action_widgets[surface.surface_id]["editor"] = SimpleNamespace(
        _action_inputs={
            "corpus_db_path": {
                "spec": {"name": "corpus_db_path", "persist_key": "corpus_db", "required": False},
                "kind": "save_file",
                "widget": _Entry(str(corpus_db_path)),
            }
        }
    )
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        captured["state_root"] = state_root
        captured["payload"] = payload
        return {"status": "completed", "count": 4, "reason": "4 Embeddings erzeugt."}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "generate_embeddings",
            "label": "Generate Embeddings",
            "contract_module": "corpus_builder.orchestrator_contract",
            "runtime_owner": "orchestrator",
            "orchestrator_action": "embeddings",
        },
    )

    assert captured["module_root"] == orchestrator_root
    assert captured["contract_module"] == "orchestrator.orchestrator_contract"
    assert captured["payload"]["action"] == "embeddings"
    assert captured["payload"]["ui_state"]["selected_corpus_db_path"] == str(corpus_db_path)
    assert captured["payload"]["ui_state"]["corpus_output_folder"] == str(corpus_root)
    assert events == ["render"]
    assert "4 Embeddings erzeugt." in operation_runner.result_text(app, surface.surface_id)


def test_generate_embeddings_without_explicit_owner_route_stays_owner_local(monkeypatch, tmp_path: Path) -> None:
    corpus_builder_root = tmp_path / "05 - Corpus Builder"
    corpus_builder_root.mkdir()
    corpus_entry = _entry(
        slot_name="05 - Corpus Builder",
        display_name="Corpus Builder",
        module_root=str(corpus_builder_root),
        module_key="corpus_builder",
        edit_contract_path="corpus_builder/edit_contract",
    )
    surface = SurfaceModel(
        surface_id="corpus_builder.embeddings_policy::action::generate_embeddings",
        label="Generate Embeddings",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={"action_buttons": [{"action": "generate_embeddings"}]},
        value={},
        draft={},
        operation_links=(),
    )
    app = SimpleNamespace(
        _pipeline_root=tmp_path,
        _state_root=tmp_path / "edit-suite-state",
        _snapshot=SimpleNamespace(entries=(corpus_entry,)),
        _ui_state={"operation_contexts": {}},
        _selected_module=corpus_entry.slot_name,
        _drafts={corpus_entry.slot_name: {}},
        _action_widgets={surface.surface_id: {"surface": surface}},
        _operation_results={},
        _render_detail_only=False,
        _selected_entry=lambda: corpus_entry,
        _render=lambda: None,
    )
    captured = {}

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        del state_root, payload
        captured["module_root"] = module_root
        captured["contract_module"] = contract_module
        return {"status": "ok"}

    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)
    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {"action": "generate_embeddings", "label": "Generate Embeddings", "contract_module": "corpus_builder.orchestrator_contract"},
    )

    assert captured["module_root"] == corpus_builder_root
    assert captured["contract_module"] == "corpus_builder.orchestrator_contract"
