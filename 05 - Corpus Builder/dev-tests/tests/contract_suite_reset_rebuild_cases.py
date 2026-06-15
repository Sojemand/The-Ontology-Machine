from __future__ import annotations

from types import SimpleNamespace

from corpus_builder.orchestrator_contract import workflow_suite


def test_workflow_suite_reset_returns_kernel_reset_proofs(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_suite,
        "reset_active_corpus_db",
        lambda *_args, **_kwargs: {
            "corpus_db_path": "C:/tmp/corpus.db",
            "database_path": "C:/tmp/corpus.db",
            "confirmation": {"artifact_path": "C:/tmp/reset-confirmation.json"},
            "semantic_release_preserved": True,
            "empty_state_proven": True,
            "active_release_ref": {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "release_fingerprint": "sha256:test",
            },
            "preserved_release_ref": {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "release_fingerprint": "sha256:test",
            },
            "post_reset_counts": {"documents": 0},
            "cleared_table_counts": {"documents": 4},
            "physical_compaction": {"attempted": True, "performed": True},
            "physical_compaction_performed": True,
            "wal_sidecar_cleanup": {"attempted": True, "removed": ["C:/tmp/corpus.db-wal"]},
        },
    )

    response = workflow_suite.handle_reset_active_corpus_db(
        SimpleNamespace(corpus_db_path="C:/tmp/corpus.db", confirmation_artifact_path="C:/tmp/reset-confirmation.json"),
        context=object(),
    )

    assert response["status"] == "ok"
    assert response["output_refs"]["database_path"] == "C:/tmp/corpus.db"
    assert response["output_refs"]["semantic_release_preserved"] is True
    assert response["output_refs"]["empty_state_proven"] is True
    assert response["output_refs"]["physical_compaction_performed"] is True
    assert response["output_refs"]["wal_sidecar_cleanup"]["attempted"] is True
    assert response["target_identity_proof"] == {"database_path": "C:/tmp/corpus.db"}
    assert response["receipt_fields"]["owner_action"] == "reset_active_corpus_db"


def test_workflow_suite_rebuild_returns_target_identity_proof(monkeypatch, tmp_path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    corpus_db = artifact_root / "Corpus" / "rebuilt.db"

    monkeypatch.setattr(
        workflow_suite,
        "rebuild_corpus_from_artifacts",
        lambda *_args, **_kwargs: {
            "pipeline_root": str(artifact_root),
            "artifact_roots": [str(artifact_root / "Documents")],
            "normalized_dir": str(artifact_root / "Documents" / "normalized"),
            "structured_dir": str(artifact_root / "Documents" / "structured"),
            "validation_dir": str(artifact_root / "Documents" / "validation"),
            "raw_dir": str(artifact_root / "Documents" / "raw"),
            "bundle_count": 0,
            "result": SimpleNamespace(loaded=0, skipped=0, archived=0, errors=0),
            "active_release_id": "release.test",
            "active_release_version": "custom.v1",
            "active_release_fingerprint": "sha256:release-test",
            "active_release_path": str(artifact_root / "Semantic Release" / "releases" / "release.test" / "release.json"),
            "corpus_db_path": str(corpus_db),
            "release_fingerprint": "sha256:release-test",
            "replace_existing": True,
            "replaced_existing": False,
        },
    )

    response = workflow_suite.handle_rebuild(
        SimpleNamespace(
            pipeline_root=str(artifact_root),
            normalized_dir=None,
            structured_dir=None,
            validation_dir=None,
            raw_dir=None,
            corpus_db_path=str(corpus_db),
            release_path=str(artifact_root / "Semantic Release" / "releases" / "release.test" / "release.json"),
            replace_existing=True,
        ),
        context=object(),
    )

    proof = response["target_identity_proof"]
    assert response["status"] == "ok"
    assert proof["database_path"] == str(corpus_db)
    assert proof["database_path_hash"].startswith("sha256:")
    assert proof["artifact_root_path"] == str(artifact_root)
    assert proof["artifact_root_path_hash"].startswith("sha256:")
    assert response["detail"]["database_path"] == str(corpus_db)
    assert response["detail"]["release_fingerprint"] == "sha256:release-test"
