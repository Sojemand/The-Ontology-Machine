from __future__ import annotations

from corpus_builder.orchestrator_contract import validation


def test_validation_accepts_suite_search_and_rebuild_payloads() -> None:
    activation = validation.parse_activate_semantic_release_command(
        {
            "action": "activate_semantic_release",
            "release_path": "C:/tmp/release.json",
            "corpus_db_path": "C:/tmp/corpus.db",
            "confirmation_artifact_path": "C:/tmp/confirmation.json",
            "write_global_mirrors": False,
        }
    )
    new_activation = validation.parse_create_and_activate_new_corpus_db_command(
        {
            "action": "create_and_activate_new_corpus_db",
            "release_path": "C:/tmp/release.json",
            "confirmation_artifact_path": "C:/tmp/new-db-confirmation.json",
        }
    )
    activated_context = validation.parse_activate_corpus_context_command(
        {
            "action": "activate_corpus_context",
            "corpus_db_path": "C:/tmp/context.db",
        }
    )
    empty_db = validation.parse_create_empty_corpus_db_command(
        {
            "action": "create_empty_corpus_db",
            "corpus_db_path": "C:/tmp/empty.db",
            "activate_context": True,
        }
    )
    reset_db = validation.parse_reset_active_corpus_db_command(
        {
            "action": "reset_active_corpus_db",
            "corpus_db_path": "C:/tmp/active.db",
            "confirmation_artifact_path": "C:/tmp/reset-confirmation.json",
        }
    )
    preflight = validation.parse_activation_preflight_command(
        {
            "action": "activation_preflight",
            "release_path": "C:/tmp/release.json",
            "corpus_db_path": "C:/tmp/corpus.db",
        }
    )
    read_active = validation.parse_read_active_semantic_release_command(
        {"action": "read_active_semantic_release", "corpus_db_path": "C:/tmp/corpus.db"}
    )
    search = validation.parse_search_command(
        {
            "action": "search",
            "corpus_db_path": "C:/tmp/corpus.db",
            "query": "invoice",
            "mode": "Hybrid",
            "limit": 5,
            "runtime_model": "text-embedding-3-large",
        }
    )
    rebuild = validation.parse_rebuild_from_artifacts_command(
        {
            "action": "rebuild_from_artifacts",
            "pipeline_root": "C:/tmp/pipeline",
            "corpus_db_path": "C:/tmp/corpus.db",
            "release_path": "C:/tmp/release.json",
            "replace_existing": False,
        }
    )
    new_rebuild = validation.parse_create_and_rebuild_new_corpus_db_command(
        {
            "action": "create_and_rebuild_new_corpus_db",
            "pipeline_root": "C:/tmp/pipeline",
            "confirmation_artifact_path": "C:/tmp/new-db-confirmation.json",
        }
    )
    basic_relation_mining = validation.parse_basic_relation_mining_command(
        {
            "action": "basic_relation_mining",
            "corpus_db_path": "C:/tmp/corpus.db",
            "dry_run": True,
        }
    )
    merge_preflight = validation.parse_merge_preflight_command(
        {
            "action": "merge_preflight",
            "source_db_path": "C:/tmp/source.corpus.db",
            "target_db_path": "C:/tmp/target.corpus.db",
        }
    )
    merge_corpus = validation.parse_merge_corpus_databases_command(
        {
            "action": "merge_corpus_databases",
            "source_db_path": "C:/tmp/source.corpus.db",
            "target_db_path": "C:/tmp/target.corpus.db",
            "snapshot_risk_confirmation_artifact_path": "C:/tmp/snapshot.json",
            "collision_resolution_artifact_path": "C:/tmp/collision.json",
        }
    )

    assert activation.confirmation_artifact_path == "C:/tmp/confirmation.json"
    assert activation.write_global_mirrors is False
    assert new_activation.confirmation_artifact_path == "C:/tmp/new-db-confirmation.json"
    assert activated_context.corpus_db_path == "C:/tmp/context.db"
    assert empty_db.activate_context is True
    assert reset_db.confirmation_artifact_path == "C:/tmp/reset-confirmation.json"
    assert preflight.release_path == "C:/tmp/release.json"
    assert read_active.corpus_db_path == "C:/tmp/corpus.db"
    assert search.mode == "Hybrid"
    assert search.runtime_model == "text-embedding-3-large"
    assert rebuild.pipeline_root == "C:/tmp/pipeline"
    assert rebuild.release_path == "C:/tmp/release.json"
    assert rebuild.replace_existing is False
    assert new_rebuild.confirmation_artifact_path == "C:/tmp/new-db-confirmation.json"
    assert basic_relation_mining.corpus_db_path == "C:/tmp/corpus.db"
    assert basic_relation_mining.dry_run is True
    assert merge_preflight.source_db_path == "C:/tmp/source.corpus.db"
    assert merge_corpus.snapshot_risk_confirmation_artifact_path == "C:/tmp/snapshot.json"
