from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.integrations import ReleaseActivationStageResult
from orchestrator.models import UiState
from orchestrator.models.snapshots import PipelineSnapshot
from orchestrator.pipeline import database_workflow


def test_execute_create_database_exports_selected_blueprint_before_activation(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = tmp_path / "Artifact Tree"
    target_db_path = tmp_path / "corpus" / "customer-default.db"
    captured: dict[str, object] = {}

    class Modules:
        def activate_semantic_release(self, release_path: Path, corpus_db_path: Path):
            captured["activate_release_path"] = release_path
            captured["activate_corpus_db_path"] = corpus_db_path
            captured["activate_corpus_db_exists"] = corpus_db_path.exists()
            return ReleaseActivationStageResult(
                status="applied",
                release_id="semantic_release.default",
                release_version="2026-03-28.v6",
                active_snapshot_id="sha256:test-snapshot",
            )

    engine = SimpleNamespace(
        _modules=Modules(),
        _snapshot=PipelineSnapshot(),
        _snapshot_callback=None,
        _runtime_lock=None,
        _thread_local=SimpleNamespace(),
        _active_log_path=None,
        _log_callback=None,
    )

    def export_default_blueprint_release(*, blueprint_ref: str, target_locale: str | None, output_path: Path) -> dict[str, object]:
        captured["blueprint_ref"] = blueprint_ref
        captured["target_locale"] = target_locale
        captured["export_output_path"] = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return {
            "blueprint_ref": blueprint_ref,
            "output_path": str(output_path),
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "runtime_locale": target_locale or "en",
        }

    engine.export_default_blueprint_release = export_default_blueprint_release

    result = database_workflow._execute_create_database(
        engine,
        ui_state=UiState(artifact_folder=str(artifact_root)),
        request={
            "database_name": "customer-default",
            "target_db_path": str(target_db_path),
            "bootstrap_mode": "default_release",
            "blueprint_ref": "default",
            "taxonomy_locale": "en",
        },
        runtime_dir=runtime_dir,
    )

    expected_release_path = artifact_root / "Semantic Release" / "default__en.semantic_release.json"
    assert captured == {
        "blueprint_ref": "default",
        "target_locale": "en",
        "export_output_path": expected_release_path,
        "activate_release_path": expected_release_path,
        "activate_corpus_db_path": target_db_path,
        "activate_corpus_db_exists": True,
    }
    assert result["blueprint_ref"] == "default"
    assert result["taxonomy_locale"] == "en"
    assert result["release_path"] == str(expected_release_path)
    assert result["release_id"] == "semantic_release.default"


def test_execute_create_database_removes_new_db_when_activation_fails(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = tmp_path / "Artifact Tree"
    target_db_path = tmp_path / "corpus" / "customer-default.db"

    class Modules:
        def activate_semantic_release(self, _release_path: Path, corpus_db_path: Path):
            assert corpus_db_path.exists()
            return ReleaseActivationStageResult(status="error", reason="activation failed")

    engine = SimpleNamespace(
        _modules=Modules(),
        _snapshot=PipelineSnapshot(),
        _snapshot_callback=None,
        _runtime_lock=None,
        _thread_local=SimpleNamespace(),
        _active_log_path=None,
        _log_callback=None,
        export_default_blueprint_release=lambda **kwargs: {
            "blueprint_ref": kwargs["blueprint_ref"],
            "output_path": str(kwargs["output_path"]),
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "runtime_locale": kwargs["target_locale"] or "en",
        },
    )

    try:
        database_workflow._execute_create_database(
            engine,
            ui_state=UiState(artifact_folder=str(artifact_root)),
            request={
                "database_name": "customer-default",
                "target_db_path": str(target_db_path),
                "bootstrap_mode": "default_release",
                "blueprint_ref": "default",
                "taxonomy_locale": "en",
            },
            runtime_dir=runtime_dir,
        )
    except RuntimeError as exc:
        assert "activation failed" in str(exc)
    else:
        raise AssertionError("expected activation failure")

    assert not target_db_path.exists()
