from __future__ import annotations

from types import SimpleNamespace

from corpus_builder.orchestrator_contract import workflow_suite
from corpus_builder.orchestrator_contract.types import BasicRelationMiningCommand


def test_workflow_suite_create_and_activate_new_corpus_db_wraps_results(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "create_and_activate_new_corpus_db",
        lambda *_args, **_kwargs: {
            "release_id": "semantic_release.default",
            "release_version": "v1",
            "corpus_root": "C:/Artefacts/Corpus",
            "corpus_db_path": "C:/Artefacts/Corpus/housing-2026-04-05-corpus-en.db",
            "previous_default_corpus_db_path": "C:/Artefacts/Corpus/corpus.db",
            "taxonomy_locale": "en",
        },
    )

    response = workflow_suite.handle_create_and_activate_new_corpus_db(
        SimpleNamespace(
            release_path="C:/tmp/release.json",
            confirmation_artifact_path="C:/tmp/new-db-confirmation.json",
        ),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "New corpus DB created and release activated"
    assert response["detail"]["corpus_db_path"].endswith("housing-2026-04-05-corpus-en.db")


def test_workflow_suite_create_and_rebuild_new_corpus_db_wraps_results(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "create_and_rebuild_new_corpus_db",
        lambda *_args, **_kwargs: {
            "pipeline_root": "C:/tmp/pipeline",
            "artifact_roots": ["C:/tmp/pipeline/normalized"],
            "normalized_dir": "C:/tmp/pipeline/normalized",
            "structured_dir": "C:/tmp/pipeline/structured",
            "validation_dir": "C:/tmp/pipeline/validation",
            "bundle_count": 2,
            "missing_structured_count": 0,
            "missing_validation_count": 0,
            "invalid_projection_files": [],
            "projection_preview": [],
            "result": SimpleNamespace(loaded=2, skipped=0, archived=0, errors=0),
            "active_release_id": "semantic_release.default",
            "active_release_version": "v1",
            "active_release_path": "C:/tmp/state/semantic_release.active.json",
            "corpus_root": "C:/Artefacts/Corpus",
            "corpus_db_path": "C:/Artefacts/Corpus/housing-2026-04-05-corpus-en.db",
            "previous_default_corpus_db_path": "C:/Artefacts/Corpus/corpus.db",
            "taxonomy_locale": "en",
        },
    )

    response = workflow_suite.handle_create_and_rebuild_new_corpus_db(
        SimpleNamespace(
            pipeline_root="C:/tmp/pipeline",
            normalized_dir=None,
            structured_dir=None,
            validation_dir=None,
            raw_dir=None,
            confirmation_artifact_path="C:/tmp/new-db-confirmation.json",
        ),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "New corpus DB created and rebuilt"
    assert response["detail"]["corpus_db_path"].endswith("housing-2026-04-05-corpus-en.db")


def test_workflow_suite_basic_relation_mining_wraps_report(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "run_basic_relation_mining",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "corpus_db_path": "C:/tmp/corpus.db",
            "dry_run": False,
            "report": {
                "status": "pass",
                "source_documents": 1,
                "source_document_pages": 2,
                "relations_inserted": 4,
                "unresolved_documents": [],
                "rejected_groups": [],
                "warnings": [],
            },
        },
    )

    response = workflow_suite.handle_basic_relation_mining(
        BasicRelationMiningCommand(corpus_db_path="C:/tmp/corpus.db"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Basic relation mining completed"
    assert response["output_refs"]["source_documents"] == 1
    assert response["output_refs"]["source_document_pages"] == 2
    assert response["output_refs"]["relations_inserted"] == 4
    assert response["receipt_fields"]["owner_action"] == "basic_relation_mining"
