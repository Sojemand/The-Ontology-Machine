from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_builder.models import EmbeddingRuntimeSettings
from corpus_builder.orchestrator_contract import workflow, workflow_dispatch
from corpus_builder.orchestrator_contract.types import ActivateSemanticReleaseCommand, HealthcheckCommand, LoadDocumentCommand


def test_workflow_load_document_maps_first_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_load_bundle(_context, **kwargs):
        captured["bundle_kwargs"] = kwargs
        return "bundle"

    def fake_load_batch(_context, bundles, *, persist_page_images_in_db=None, page_images_dir=None):
        captured["bundles"] = bundles
        captured["persist_page_images_in_db"] = persist_page_images_in_db
        captured["page_images_dir"] = page_images_dir
        return SimpleNamespace(results=[SimpleNamespace(status="loaded", reason="")])

    monkeypatch.setattr(workflow, "build_load_bundle", fake_build_load_bundle)
    monkeypatch.setattr(workflow, "load_batch", fake_load_batch)

    result = workflow.load_document(
        LoadDocumentCommand(
            corpus_db_path="C:/tmp/corpus.db",
            normalized_path="C:/tmp/doc.structured.normalized.json",
            structured_path="C:/tmp/doc.structured.json",
            validation_path="C:/tmp/doc.validation_report.json",
        ),
        context=object(),
    )

    assert result == {"status": "loaded", "reason": ""}
    assert captured["bundles"] == ["bundle"]
    assert captured["persist_page_images_in_db"] is None
    assert captured["page_images_dir"] is None
    assert captured["bundle_kwargs"] == {
        "normalized_path": "C:/tmp/doc.structured.normalized.json",
        "structured_path": "C:/tmp/doc.structured.json",
        "validation_path": "C:/tmp/doc.validation_report.json",
        "raw_path": None,
        "corpus_db_path": "C:/tmp/corpus.db",
    }


def test_workflow_activate_semantic_release_stages_and_applies_release(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, str | bool | None] = {}
    (tmp_path / "corpus.db").write_text("db", encoding="utf-8")

    def fake_apply(_context, *, release_path=None, corpus_db_path=None, confirmation_artifact_path=None, write_global_mirrors=True):
        captured["release_path"] = str(release_path) if release_path is not None else None
        captured["corpus_db_path"] = str(corpus_db_path) if corpus_db_path is not None else None
        captured["confirmation_artifact_path"] = str(confirmation_artifact_path) if confirmation_artifact_path is not None else None
        captured["write_global_mirrors"] = write_global_mirrors
        return {"release_id": "default", "release_version": "v1"}

    monkeypatch.setattr(workflow, "apply_semantic_release", fake_apply)
    monkeypatch.setattr(workflow, "resolve_existing_corpus_db_path", lambda _context, corpus_db_path=None: Path(str(corpus_db_path)))

    result = workflow.activate_semantic_release(
        ActivateSemanticReleaseCommand(
            release_path=str(tmp_path / "semantic_release.json"),
            corpus_db_path=str(tmp_path / "corpus.db"),
            write_global_mirrors=False,
        ),
        context=object(),
    )

    assert result["status"] == "applied"
    assert result["release_id"] == "default"
    assert result["release_version"] == "v1"
    assert captured == {
        "release_path": str(tmp_path / "semantic_release.json"),
        "corpus_db_path": str(tmp_path / "corpus.db"),
        "confirmation_artifact_path": None,
        "write_global_mirrors": False,
    }


def test_dispatch_rebuild_allows_missing_target_db_to_reach_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target_db = tmp_path / "Artifact Tree" / "Corpus" / "rebuilt.db"
    captured: dict[str, object] = {}

    def fake_parse(payload: dict) -> SimpleNamespace:
        return SimpleNamespace(
            pipeline_root=payload["pipeline_root"],
            normalized_dir=None,
            structured_dir=None,
            validation_dir=None,
            raw_dir=None,
            corpus_db_path=payload["corpus_db_path"],
            release_path=payload["release_path"],
            replace_existing=True,
        )

    def fake_handler(command: SimpleNamespace, *, context: object) -> dict:
        captured["corpus_db_path"] = command.corpus_db_path
        captured["target_exists_before_handler"] = Path(command.corpus_db_path).exists()
        return {"status": "ok", "detail": {"corpus_db_path": command.corpus_db_path}}

    monkeypatch.setitem(
        workflow_dispatch._SUITE_HANDLERS,
        "rebuild_from_artifacts",
        ("parse_rebuild_from_artifacts_command_fn", fake_handler),
    )

    response = workflow_dispatch.dispatch(
        {
            "action": "rebuild_from_artifacts",
            "pipeline_root": str(tmp_path / "Artifact Tree"),
            "corpus_db_path": str(target_db),
            "release_path": str(tmp_path / "Artifact Tree" / "Semantic Release" / "releases" / "release.test" / "release.json"),
            "replace_existing": True,
        },
        context=object(),
        require_action_fn=lambda payload: payload["action"],
        request_body_fn=lambda payload: payload,
        parse_rebuild_from_artifacts_command_fn=fake_parse,
    )

    assert response["status"] == "ok"
    assert captured == {"corpus_db_path": str(target_db), "target_exists_before_handler": False}


def test_workflow_healthcheck_reports_missing_embeddings_as_optional_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "corpus_builder.orchestrator_contract.workflow_healthcheck.resolve_runtime_capability",
        lambda: SimpleNamespace(
            status="unavailable",
            api_key=None,
            reason="Keine Embeddings-API vom Orchestrator bereitgestellt.",
        ),
    )

    result = workflow.healthcheck(
        HealthcheckCommand(
            runtime_settings=EmbeddingRuntimeSettings(model="text-embedding-3-small"),
            scope="pipeline_run",
        ),
        context=object(),
    )

    assert result["status"] == "ok"
    assert result["healthy"] is True
    assert result["dependencies"][0]["name"] == "embedding_provider"
    assert result["dependencies"][0]["required"] is False
    assert result["dependencies"][0]["healthy"] is False
