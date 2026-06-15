from __future__ import annotations

from types import SimpleNamespace

from corpus_builder.orchestrator_contract import workflow_suite


def test_workflow_suite_merge_preflight_wraps_results_in_standard_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "merge_preflight",
        lambda *_args, **_kwargs: {
            "source_db_path": "C:/tmp/source.corpus.db",
            "target_db_path": "C:/tmp/target.corpus.db",
            "master_taxonomy_release_id": "master.default@1",
            "blocked": False,
            "merge_ready": False,
            "snapshot_risk_confirmation_required": True,
            "collision_resolution_required": False,
            "pending_interactions": [{"kind": "snapshot_risk_confirmation"}],
        },
    )

    response = workflow_suite.handle_merge_preflight(
        SimpleNamespace(source_db_path="C:/tmp/source.corpus.db", target_db_path="C:/tmp/target.corpus.db"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Corpus merge preflight completed"
    assert response["detail"]["snapshot_risk_confirmation_required"] is True


def test_workflow_suite_read_active_release_wraps_results_in_standard_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "read_active_semantic_release",
        lambda *_args, **_kwargs: {
            "release_id": "semantic_release.default",
            "release_version": "1",
            "fingerprint": "sha256:test",
            "release_path": "C:/tmp/state/semantic_release.active.json",
            "status": {"active_release_id": "semantic_release.default"},
            "release": {"release_id": "semantic_release.default"},
        },
    )

    response = workflow_suite.handle_read_active_semantic_release(
        SimpleNamespace(corpus_db_path="C:/tmp/corpus.db"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Active semantic release loaded"
    assert response["detail"]["fingerprint"] == "sha256:test"
    assert response["detail"]["release"]["release_id"] == "semantic_release.default"


def test_workflow_suite_activation_preflight_wraps_results_in_standard_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "activation_preflight",
        lambda *_args, **_kwargs: {
            "current_snapshot": {"snapshot_id": "sha256:old"},
            "next_snapshot": {"snapshot_id": "sha256:new"},
            "recommended_confirmation_filename": "activation_confirmation.json",
        },
    )

    response = workflow_suite.handle_activation_preflight(
        SimpleNamespace(release_path="C:/tmp/release.json", corpus_db_path="C:/tmp/corpus.db"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Semantic activation preflight completed"
    assert response["detail"]["next_snapshot"]["snapshot_id"] == "sha256:new"


def test_workflow_suite_search_wraps_results_in_standard_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "search_corpus",
        lambda *_args, **_kwargs: [
            SimpleNamespace(document_id="doc-1", title="Invoice", snippet="...", score=0.9, source="fts"),
        ],
    )

    response = workflow_suite.handle_search(
        SimpleNamespace(corpus_db_path="C:/tmp/corpus.db", query="invoice", mode="Fulltext", limit=10, runtime_model=None),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Search completed"
    assert response["summary_lines"] == ["Mode: Fulltext", "Hits: 1"]
    assert response["table"]["rows"][0]["document_id"] == "doc-1"


def test_workflow_suite_rebuild_preview_exposes_preview_detail(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "build_rebuild_bundles_from_artifacts",
        lambda *_args, **_kwargs: {
            "pipeline_root": "C:/tmp/pipeline",
            "artifact_roots": ["C:/tmp/pipeline/normalized"],
            "normalized_dir": "C:/tmp/pipeline/normalized",
            "structured_dir": "C:/tmp/pipeline/structured",
            "validation_dir": "C:/tmp/pipeline/validation",
            "bundle_count": 2,
            "missing_structured_count": 0,
            "missing_validation_count": 1,
            "invalid_projection_files": [],
            "projection_preview": [{"projection_id": "finance.default.v1"}],
        },
    )

    response = workflow_suite.handle_preview_rebuild(
        SimpleNamespace(pipeline_root="C:/tmp/pipeline", normalized_dir=None, structured_dir=None, validation_dir=None, corpus_db_path="C:/tmp/corpus.db"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Rebuild preview completed"
    assert response["detail"]["bundle_count"] == 2
    assert response["detail"]["projection_preview"][0]["projection_id"] == "finance.default.v1"
