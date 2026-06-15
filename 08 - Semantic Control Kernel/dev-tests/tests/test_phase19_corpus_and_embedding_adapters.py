from __future__ import annotations

from phase19_adapter_unblock_support import (
    AdapterCallResult,
    CorpusAdapter,
    EmbeddingAdapter,
    PIPELINE_ROOT,
    _adapters,
    _seed_analysis_database,
)

def test_rebuild_adapter_translates_kernel_payload_to_owner_rebuild_action(tmp_path: Path) -> None:
    corpus = CorpusAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    captured: list[dict[str, object]] = []

    def capture_invoke(**kwargs):
        captured.append(dict(kwargs))
        return AdapterCallResult(
            {
                "adapter_call_id": "capture_rebuild",
                "adapter_name": "corpus",
                "capability_status": "implemented_in_pipeline",
                "diagnostics": [],
                "kernel_function": kwargs["kernel_function"],
                "output_refs": {},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    corpus.invoke = capture_invoke
    artifact_root = tmp_path / "Artifact Tree"
    database_path = artifact_root / "Corpus" / "rebuilt.db"

    result = corpus.rebuild_from_artifacts(
        {
            "artifact_root": str(artifact_root),
            "corpus_db_path": str(database_path),
            "loaded_semantic_release": {
                "loaded_release_fingerprint": "sha256:release",
                "loaded_release_path": str(artifact_root / "Semantic Release" / "releases" / "release.test" / "release.json"),
            },
            "replace_existing": True,
            "target_identity": {"target_database_path": str(database_path)},
            "workflow_run_id": "wr_rebuild",
        }
    )

    owner_payload = captured[0]["request_payload"]
    target_identity = captured[0]["target_identity"]
    assert result.status == "ok"
    assert captured[0]["owner_action"] == "rebuild_from_artifacts"
    assert owner_payload == {
        "action": "rebuild_from_artifacts",
        "pipeline_root": str(artifact_root),
        "corpus_db_path": str(database_path),
        "replace_existing": True,
        "release_path": str(artifact_root / "Semantic Release" / "releases" / "release.test" / "release.json"),
    }
    assert target_identity["database_path_hash"] == corpus.owner_path_hash(database_path)
    assert target_identity["artifact_root_path_hash"] == corpus.owner_path_hash(artifact_root)

def test_embedding_adapter_routes_through_orchestrator_owner(tmp_path: Path) -> None:
    embedding = EmbeddingAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    captured: list[dict[str, object]] = []

    def capture_invoke(**kwargs):
        captured.append(dict(kwargs))
        return AdapterCallResult(
            {
                "adapter_call_id": "capture_embeddings",
                "adapter_name": "embedding",
                "capability_status": "implemented_in_pipeline",
                "diagnostics": [],
                "kernel_function": kwargs["kernel_function"],
                "output_refs": {"embedding_result": "completed"},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    embedding.invoke = capture_invoke
    database_path = tmp_path / "Artifact Tree" / "Corpus" / "rebuilt.db"

    result = embedding.create_embeddings({"corpus_db_path": str(database_path)})

    owner_payload = captured[0]["request_payload"]
    ui_state = owner_payload["ui_state"]
    target_identity = captured[0]["target_identity"]
    assert result.status == "ok"
    assert captured[0]["owner_module"] == "00 - Orchestrator"
    assert captured[0]["owner_action"] == "embeddings"
    assert owner_payload["action"] == "embeddings"
    assert ui_state["selected_corpus_db_path"] == str(database_path.resolve(strict=False))
    assert ui_state["corpus_output_folder"] == str(database_path.resolve(strict=False).parent)
    assert target_identity["database_path_hash"] == embedding.owner_path_hash(database_path)

def test_backfill_sql_owner_proves_generic_database_path_hash(tmp_path: Path) -> None:
    _workspace, corpus, _semantic, _batch, _merge = _adapters(tmp_path)
    artifact_root = tmp_path / "Artifact Tree"
    database_path = artifact_root / "Corpus" / "active.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    _seed_analysis_database(artifact_root)

    result = corpus.backfill_sql(
        {
            "artifact_root": str(artifact_root),
            "merge_run_id": "merge_backfill",
            "target_database_path": str(database_path),
            "id_map": {
                "mappings": [
                    {
                        "target_document_id": "doc_1",
                        "semantic_release_version": "custom.v1",
                        "release_fingerprint": "sha256:merged",
                        "projection_id": "projection_merged",
                        "projection_fingerprint": "sha256:projection_merged",
                    }
                ]
            },
            "target_identity": {},
        }
    )
    proof = result.to_dict()["target_identity_proof"]

    assert result.status == "ok"
    assert proof["database_path_hash"] == corpus.owner_path_hash(database_path)
    assert proof["target_database_path_hash"] == proof["database_path_hash"]
