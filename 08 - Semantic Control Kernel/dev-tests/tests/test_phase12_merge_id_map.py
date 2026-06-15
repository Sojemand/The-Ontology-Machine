from __future__ import annotations

import pytest

from semantic_control_kernel.validation.merge_validation import validate_id_map
from semantic_control_kernel.workflows.merge.id_map import build_id_map, target_pipeline_batch_id


def _mapping(**overrides):
    base = {
        "projection_fingerprint": "sha256:projection",
        "projection_id": "projection.default",
        "release_fingerprint": "sha256:release",
        "semantic_release_id": "release.source",
        "semantic_release_version": "1.0.0",
        "source_artifact_path": "Documents/originals/a.pdf",
        "source_content_hash": "sha256:content",
        "source_database_id": "source_db_a",
        "source_database_path": "C:/source/corpus.db",
        "source_document_id": "doc_a",
        "source_embedding_id": "emb_a",
        "source_original_file_name": "a.pdf",
        "source_pipeline_batch_id": "batch_001",
        "source_record_id": "record_a",
        "target_artifact_path": "Documents/originals/source_db_a/a.pdf",
        "target_document_id": "target_doc_a",
        "target_embedding_id": "target_emb_a",
        "target_pipeline_batch_id": "",
        "target_record_id": "target_record_a",
        "taxonomy_fingerprint": "sha256:taxonomy",
    }
    base.update(overrides)
    return base


def test_id_map_required_fields_and_traceability() -> None:
    id_map = build_id_map(
        merge_run_id="merge_id",
        source_databases=[{"source_database_id": "source_db_a"}],
        target_database_path="C:/target/Corpus/corpus.db",
        mappings=[_mapping()],
    ).to_dict()

    validate_id_map(id_map)
    assert id_map["record_count"] == 1
    assert id_map["mappings"][0]["source_record_id"] == "record_a"
    assert id_map["mappings"][0]["target_record_id"] == "target_record_a"


def test_batch_namespacing_uses_source_database_id_on_collision() -> None:
    assert target_pipeline_batch_id(source_database_id="source_db_a", source_pipeline_batch_id="batch_001", collides=True) == "source_db_a.batch_001"


def test_batch_collision_detection_namespaces_all_colliding_source_batches() -> None:
    id_map = build_id_map(
        merge_run_id="merge_batch_collision",
        source_databases=[
            {"source_database_id": "source_db_a", "source_database_path": "C:/source/a.db"},
            {"source_database_id": "source_db_b", "source_database_path": "C:/source/b.db"},
        ],
        target_database_path="C:/target/Corpus/corpus.db",
        mappings=[
            _mapping(source_database_path="C:/source/a.db"),
            _mapping(
                source_database_id="source_db_b",
                source_database_path="C:/source/b.db",
                source_record_id="record_b",
                source_document_id="doc_b",
                source_embedding_id="emb_b",
                target_record_id="target_record_b",
                target_document_id="target_doc_b",
                target_embedding_id="target_emb_b",
            ),
        ],
    ).to_dict()

    assert [item["target_pipeline_batch_id"] for item in id_map["mappings"]] == [
        "source_db_a.batch_001",
        "source_db_b.batch_001",
    ]


def test_id_map_rejects_mapping_for_unknown_source_database() -> None:
    with pytest.raises(ValueError, match="source_database_id"):
        build_id_map(
            merge_run_id="merge_unknown_source",
            source_databases=[{"source_database_id": "source_db_a"}],
            target_database_path="C:/target/Corpus/corpus.db",
            mappings=[_mapping(source_database_id="ghost_source")],
        )


def test_artifact_path_and_embedding_remap_are_required() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        build_id_map(
            merge_run_id="merge_id",
            source_databases=[{"source_database_id": "source_db_a"}],
            target_database_path="C:/target/Corpus/corpus.db",
            mappings=[_mapping(target_artifact_path="", target_embedding_id="")],
        )


def test_fingerprint_validation_rejects_id_map_mutation() -> None:
    id_map = build_id_map(
        merge_run_id="merge_id",
        source_databases=[{"source_database_id": "source_db_a"}],
        target_database_path="C:/target/Corpus/corpus.db",
        mappings=[_mapping()],
    ).to_dict()
    id_map["record_count"] = 2

    with pytest.raises(ValueError):
        validate_id_map(id_map)
