from __future__ import annotations

from operation_runner_support import *  # noqa: F403
from edit_suite import validation

def test_merge_action_preflights_first_and_persists_confirmation_artifact(monkeypatch, tmp_path: Path) -> None:
    surface = SurfaceModel(
        surface_id="corpus_builder.settings::action::merge_corpus_databases",
        label="Merge Corpus DBs",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={"action_buttons": [{"action": "merge_corpus_databases"}]},
        value={},
        draft={},
        operation_links=(),
    )
    app, entry, events = _app(surface)
    app._state_root = tmp_path / "state"
    app.resolve_merge_interaction = lambda surface_id, choice_id: operation_runner.resolve_merge_interaction(app, surface_id, choice_id)
    app._action_widgets[surface.surface_id]["editor"] = SimpleNamespace(
        _action_inputs={
            "source_db_path": {
                "spec": {"name": "source_db_path", "persist_key": "source_db_path", "required": True},
                "kind": "open_file",
                "widget": _Entry("C:/tmp/source.corpus.db"),
            },
            "target_db_path": {
                "spec": {"name": "target_db_path", "persist_key": "target_db_path", "required": True},
                "kind": "open_file",
                "widget": _Entry("C:/tmp/target.corpus.db"),
            },
        }
    )
    captured = {"payloads": []}
    pending = {}

    def fake_start(_app, *, work, deliver):
        pending["work"] = work
        pending["deliver"] = deliver

    def fake_invoke(*, module_root, contract_module, state_root, payload):
        captured["payloads"].append(payload)
        if payload["action"] == "merge_preflight":
            return {
                "status": "ok",
                "headline": "Corpus merge preflight completed",
                "summary_lines": ["Merge state: pending_confirmation"],
                "detail": {
                    "blocked": False,
                    "pending_interactions": [
                        {
                            "kind": "snapshot_risk_confirmation",
                            "headline": "Semantic Snapshot korrupt oder unvollstaendig. DB trotzdem mergen?",
                            "summary_lines": ["Die semantische Provenance ist danach nicht voll verlaesslich."],
                            "choices": [
                                {"choice_id": "cancel_merge", "label": "Nein, Merge abbrechen", "decision": None},
                                {"choice_id": "confirm_snapshot_risk", "label": "Ja, trotzdem mergen", "decision": "merge_anyway"},
                            ],
                            "artifact_argument_name": "snapshot_risk_confirmation_artifact_path",
                            "artifact_template": {
                                "artifact_version": "semantic_merge_snapshot_risk_confirmation_v1",
                                "source_db_path": "C:/tmp/source.corpus.db",
                                "target_db_path": "C:/tmp/target.corpus.db",
                                "decision": "merge_anyway",
                            },
                            "recommended_filename": "snapshot-risk.json",
                        }
                    ],
                },
            }
        return {"status": "ok", "headline": "Corpus merge completed", "summary_lines": ["Imported documents: 1"]}

    monkeypatch.setattr(operation_runner.background_jobs, "start", fake_start)
    monkeypatch.setattr(operation_runner, "invoke_module_contract", fake_invoke)

    operation_runner.run_surface_action(
        app,
        surface.surface_id,
        {
            "action": "merge_corpus_databases",
            "label": "Merge Corpus DBs",
            "contract_module": "corpus_builder.orchestrator_contract",
        },
    )
    pending["deliver"](pending["work"](), None)

    assert captured["payloads"][0]["action"] == "merge_preflight"
    assert operation_runner.merge_interaction_choices(app, surface.surface_id)[1]["label"] == "Ja, trotzdem mergen"

    operation_runner.resolve_merge_interaction(app, surface.surface_id, "confirm_snapshot_risk")
    pending["deliver"](pending["work"](), None)

    assert captured["payloads"][1]["action"] == "merge_corpus_databases"
    assert captured["payloads"][1]["snapshot_risk_confirmation_artifact_path"].endswith("snapshot-risk.json")
    assert events == ["render", "render"]
    assert "Snapshot Confirmation:" in operation_runner.result_text(app, surface.surface_id)

def test_merge_confirmation_filename_cannot_escape_state_root(tmp_path: Path) -> None:
    surface = _surface()
    app, _entry, _events = _app(surface)
    app._state_root = tmp_path / "state"
    app._selected_module = "05 - Corpus Builder"

    artifact_path = operation_runner._write_merge_artifact(
        app,
        surface.surface_id,
        {
            "recommended_filename": "../outside.json",
            "artifact_template": {"artifact_version": "test"},
        },
        "merge_anyway",
    )

    assert artifact_path.name == "outside.json"
    assert artifact_path.resolve().is_relative_to(app._state_root.resolve())
    assert not (tmp_path / "outside.json").exists()

def test_merge_confirmation_long_owner_segments_are_path_budgeted(tmp_path: Path) -> None:
    surface = SurfaceModel(
        surface_id="normalizer." + "very_long_surface_segment_" * 8,
        label="Long Surface",
        kind="operation",
        editable=False,
        editor_kind="operation",
        descriptor={},
        value={},
        draft={},
        operation_links=(),
    )
    app, _entry, _events = _app(surface)
    app._state_root = tmp_path / "state"
    app._selected_module = "05 - " + "Corpus Builder " * 8

    artifact_path = operation_runner._write_merge_artifact(
        app,
        surface.surface_id,
        {
            "recommended_filename": "snapshot-risk-" * 20 + ".json",
            "artifact_template": {"artifact_version": "test"},
        },
        "merge_anyway",
    )

    relative_parts = artifact_path.relative_to(app._state_root).parts
    owner_parts = [part for part in relative_parts if part != "merge-confirmations"]
    assert all(len(part) <= validation.MAX_SAFE_FILENAME_LENGTH for part in owner_parts)
    assert artifact_path.name.endswith(".json")
    assert artifact_path.resolve().is_relative_to(app._state_root.resolve())

def test_merge_confirmation_artifact_replaces_existing_file_atomically(tmp_path: Path) -> None:
    surface = _surface()
    app, _entry, _events = _app(surface)
    app._state_root = tmp_path / "state"
    app._selected_module = "05 - Corpus Builder"
    target = app._state_root / "merge-confirmations" / "05_-_Corpus_Builder" / surface.surface_id / "snapshot-risk.json"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")
    hardlink = tmp_path / "snapshot-risk-hardlink.json"
    _hardlink_or_skip(target, hardlink)

    artifact_path = operation_runner._write_merge_artifact(
        app,
        surface.surface_id,
        {
            "recommended_filename": "snapshot-risk.json",
            "artifact_template": {"artifact_version": "test"},
        },
        "merge_anyway",
    )

    assert hardlink.read_text(encoding="utf-8") == "old"
    assert json.loads(artifact_path.read_text(encoding="utf-8"))["decision"] == "merge_anyway"

def test_new_corpus_db_confirmation_artifact_replaces_existing_file_atomically(tmp_path: Path) -> None:
    app = SimpleNamespace(_state_root=tmp_path / "state", _selected_module="05 - Corpus Builder")
    target = app._state_root / "corpus-db-confirmations" / "05_-_Corpus_Builder" / "normalizer.taxonomy_release_draft" / "materialize.json"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")
    hardlink = tmp_path / "corpus-confirmation-hardlink.json"
    _hardlink_or_skip(target, hardlink)

    artifact_path = corpus_db_dialog_support.write_confirmation_artifact(
        app,
        "normalizer.taxonomy_release_draft",
        action="materialize",
        database_label="Main Corpus",
        taxonomy_locale="DE",
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert hardlink.read_text(encoding="utf-8") == "old"
    assert payload["confirmed"] is True
    assert payload["taxonomy_locale"] == "de"

def test_new_corpus_db_preview_filename_is_path_budgeted() -> None:
    name = corpus_db_dialog_support.build_filename("audit-corpus-" * 20, "de")

    assert len(name) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert name.endswith(".db")
