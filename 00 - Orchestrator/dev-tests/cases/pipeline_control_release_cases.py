from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.pipeline import OrchestratorEngine
from orchestrator.pipeline import release_workflow as pipeline_release_workflow
from tests.pipeline_harness import create_source, make_engine, make_ui_state, orchestrator_logs_root

from cases.pipeline_control_support import ReleaseAwareModules, ReleaseFailingModules, assert_no_route_artifacts


def test_run_requires_explicit_release_activation_before_healthcheck(tmp_path: Path) -> None:
    ui_state, release_path = _release_ui_state(tmp_path)
    create_source(ui_state)
    modules = ReleaseAwareModules()
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    with pytest.raises(RuntimeError, match="Activate"):
        engine.run(ui_state)

    assert modules.release_events == [
        ("preflight", str(release_path), str(Path(ui_state.corpus_output_folder) / "corpus.db")),
    ]
    assert engine.snapshot.stage_statuses["Corpus Builder"].status == "Error"


def test_activate_release_then_run_uses_selected_release_without_hidden_switch(tmp_path: Path) -> None:
    ui_state, release_path = _release_ui_state(tmp_path)
    create_source(ui_state)
    modules = ReleaseAwareModules()
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)
    preflight = engine.activation_preflight(ui_state)
    confirmation_payload = pipeline_release_workflow.build_confirmation_payload(
        preflight,
        corpus_db_path=Path(ui_state.corpus_output_folder) / "corpus.db",
        decision="activate_only",
    )

    engine.activate_release(ui_state, confirmation_payload=confirmation_payload)
    modules.release_events.clear()

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert modules.release_events[:3] == [
        ("preflight", str(release_path), str(Path(ui_state.corpus_output_folder) / "corpus.db")),
        ("healthcheck", ("optimizer", "interpreter", "validator", "normalizer", "corpus_builder")),
        ("read_active", str(Path(ui_state.corpus_output_folder) / "corpus.db")),
    ]
    runtime_assets = list((orchestrator_logs_root(tmp_path) / "runs").rglob("runtime_semantic_assets.json"))
    assert len(runtime_assets) == 1
    assert modules.runtime_semantic_asset_builds == []
    assert engine.snapshot.stage_statuses["Runtime Semantics"].status == "Done"


def test_activate_release_failure_names_selected_release_path(tmp_path: Path) -> None:
    ui_state, release_path = _release_ui_state(tmp_path)
    create_source(ui_state)
    modules = ReleaseFailingModules("projections[0].routing.surface_signals must be a JSON object.")
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    with pytest.raises(RuntimeError, match="surface_signals") as excinfo:
        engine.activate_release(ui_state)

    assert f"release_path={release_path}" in str(excinfo.value)
    assert modules.release_events == [("activate", str(release_path))]


def test_activate_release_writes_confirmation_artifact_for_module_call(tmp_path: Path) -> None:
    class ConfirmingModules(ReleaseAwareModules):
        def __init__(self) -> None:
            super().__init__()
            self.confirmation_payload: dict[str, object] | None = None

        def activate_semantic_release(self, release_path: Path, corpus_db_path: Path, confirmation_artifact_path: Path | None = None):
            result = super().activate_semantic_release(release_path, corpus_db_path, confirmation_artifact_path)
            assert confirmation_artifact_path is not None
            self.confirmation_payload = json.loads(confirmation_artifact_path.read_text(encoding="utf-8"))
            return result

    ui_state, release_path = _release_ui_state(tmp_path)
    modules = ConfirmingModules()
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)
    payload = {
        "artifact_version": "semantic_activation_confirmation_v1",
        "corpus_db_path": str(Path(ui_state.corpus_output_folder) / "corpus.db"),
        "release_path": str(release_path),
        "expected_current_snapshot_id": "sha256:old",
        "expected_new_snapshot_id": "sha256:new",
        "expected_release_fingerprint": "sha256:semantic-default",
        "expected_master_taxonomy_release_id": "sha256:master-line",
        "expected_runtime_locale": "en",
        "decision": "activate_only",
    }

    engine.activate_release(ui_state, confirmation_payload=payload)

    assert modules.confirmation_payload == payload


def test_run_fails_early_when_no_active_or_selected_release_exists(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    modules = ReleaseAwareModules()
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)

    with pytest.raises(RuntimeError, match="Active semantic release is missing"):
        engine.run(ui_state)

    assert source.exists()
    assert modules.release_events == [
        ("healthcheck", ("optimizer", "interpreter", "validator", "normalizer", "corpus_builder")),
        ("read_active", str(Path(ui_state.corpus_output_folder) / "corpus.db")),
    ]
    assert engine.snapshot.stage_statuses["Runtime Semantics"].status == "Error"
    assert_no_route_artifacts(ui_state)


def test_run_builds_fresh_runtime_semantics_cache_per_run(tmp_path: Path) -> None:
    engine = make_engine(tmp_path, scenarios={})
    ui_state_a = make_ui_state(tmp_path / "corpus-a")
    ui_state_b = make_ui_state(tmp_path / "corpus-b")
    create_source(ui_state_a, "doc-a.pdf")
    create_source(ui_state_b, "doc-b.pdf", content="doc-b")
    original_read_active = engine._modules.read_active_semantic_release

    def read_active_semantic_release(corpus_db_path: Path) -> dict[str, object]:
        detail = original_read_active(corpus_db_path)
        snapshot_id = f"sha256:{corpus_db_path.parent.name}"
        active_snapshot = dict(detail["active_snapshot"])
        active_snapshot["snapshot_id"] = snapshot_id
        active_snapshot["release"] = {**active_snapshot["release"], "active_snapshot": {"snapshot_id": snapshot_id, "release_path": active_snapshot["release_path"]}}
        return {**detail, "active_snapshot": active_snapshot}

    engine._modules.read_active_semantic_release = read_active_semantic_release

    first = engine.run(ui_state_a)
    second = engine.run(ui_state_b)

    assert first.success == 1
    assert second.success == 1
    runtime_assets = list((orchestrator_logs_root(tmp_path) / "runs").rglob("runtime_semantic_assets.json"))
    assert len(runtime_assets) == 2
    assert engine._modules.runtime_semantic_release_reads == [
        str(Path(ui_state_a.corpus_output_folder) / "corpus.db"),
        str(Path(ui_state_b.corpus_output_folder) / "corpus.db"),
    ]


def _release_ui_state(tmp_path: Path):
    ui_state = make_ui_state(tmp_path)
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text("{}", encoding="utf-8")
    ui_state.semantic_release_path = str(release_path)
    ui_state.semantic_release_mode = "override_selected"
    return ui_state, release_path
