from __future__ import annotations

from types import SimpleNamespace

from corpus_builder.models import EmbeddingRuntimeSettings
from corpus_builder.services import apply_semantic_release, create_empty_corpus_db
from corpus_builder.orchestrator_contract.types import HealthcheckCommand
from corpus_builder.orchestrator_contract import workflow
from corpus_builder.orchestrator_contract import workflow_healthcheck
from tests.fixtures.semantic_context import make_semantic_context


def test_healthcheck_blocks_pipeline_run_when_active_release_is_missing(
    tmp_path,
    monkeypatch,
) -> None:
    context = make_semantic_context(tmp_path)
    (context.state_dir / "semantic_release.active.json").unlink()
    monkeypatch.setattr(
        workflow_healthcheck,
        "resolve_runtime_capability",
        lambda: SimpleNamespace(status="unavailable", api_key=None, reason="Embeddings optional"),
    )

    result = workflow.healthcheck(
        HealthcheckCommand(
            runtime_settings=EmbeddingRuntimeSettings(model="text-embedding-3-small"),
            scope="pipeline_run",
        ),
        context=context,
    )

    assert result["status"] == "ok"
    assert result["healthy"] is False
    assert "Kein aktiver Semantic Release vorhanden" in result["message"]
    assert "Waehle im Orchestrator" in result["message"]


def test_healthcheck_accepts_target_scoped_active_release_snapshot(
    tmp_path,
    monkeypatch,
) -> None:
    context = make_semantic_context(tmp_path)
    active_mirror = context.state_dir / "semantic_release.active.json"
    release_path = context.config_dir / "semantic_release.default.json"
    corpus_db_path = tmp_path / "Artifact Tree" / "Corpus" / "corpus.db"
    create_empty_corpus_db(context, corpus_db_path=corpus_db_path)
    apply_semantic_release(
        context,
        release_path=release_path,
        corpus_db_path=corpus_db_path,
        write_global_mirrors=False,
    )
    active_mirror.unlink()
    monkeypatch.setattr(
        workflow_healthcheck,
        "resolve_runtime_capability",
        lambda: SimpleNamespace(status="unavailable", api_key=None, reason="Embeddings optional"),
    )

    result = workflow.healthcheck(
        HealthcheckCommand(
            runtime_settings=EmbeddingRuntimeSettings(model="text-embedding-3-small"),
            scope="pipeline_run",
            corpus_db_path=str(corpus_db_path),
        ),
        context=context,
    )

    assert result["status"] == "ok"
    assert result["healthy"] is True
    assert result["message"] == ""
