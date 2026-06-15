from __future__ import annotations

import struct
from types import SimpleNamespace

import pytest

from .search_surface_support import RUNTIME_SETTINGS, load_from_file
from corpus_builder.embeddings import store_embedding
from corpus_builder.search import hybrid_search, semantic_search


def test_semantic_and_hybrid_search_ignore_archived_docs(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    first = dict(vision_structured)
    first["source"] = dict(vision_structured["source"])
    first["source"]["content_hash"] = "sha256:first-semantic"
    second = dict(vision_structured)
    second["source"] = dict(vision_structured["source"])
    second["source"]["content_hash"] = "sha256:second-semantic"

    path_one = make_input_pair("semantic_old", first, vision_report=vision_validation_report)
    path_two = make_input_pair("semantic_new", second, vision_report=vision_validation_report)
    assert load_from_file(db, path_one).status == "loaded"
    assert load_from_file(db, path_two).status == "archived_and_loaded"

    store_embedding(db, "semantic_old", "old", [1.0, 0.0, 0.0], "test-model")
    store_embedding(db, "semantic_new", "new", [1.0, 0.0, 0.0], "test-model")
    db.commit()

    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[1.0, 0.0, 0.0] for _ in texts],
    )

    semantic_results = semantic_search(db, "Schlussrechnung", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key="injected-secret")
    hybrid_results = hybrid_search(db, "Schlussrechnung", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key="injected-secret")

    assert semantic_results
    assert semantic_results[0].document_id == "semantic_new"
    assert all(result.document_id != "semantic_old" for result in semantic_results)
    assert hybrid_results
    assert hybrid_results[0].document_id == "semantic_new"


def test_semantic_search_without_runtime_capability_fails_closed(db) -> None:
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES ('doc_a', 'a.pdf', 'C:/docs/a.pdf', 'sha256:a', 'invoice', 'finance', 'de', 'm', 0.9, 'pass', '2026-01-01T00:00:00Z')"
    )
    store_embedding(db, "doc_a", "a", [1.0, 0.0, 0.0], "test-model")
    db.commit()

    with pytest.raises(RuntimeError, match="Keine Embeddings-API vom Orchestrator bereitgestellt"):
        semantic_search(db, "query", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key=None)


def test_semantic_search_accepts_local_provider_without_api_key(db, monkeypatch) -> None:
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES ('doc_local', 'local.pdf', 'C:/docs/local.pdf', 'sha256:local', 'invoice', 'finance', 'de', 'm', 0.9, 'pass', '2026-01-01T00:00:00Z')"
    )
    store_embedding(db, "doc_local", "local", [1.0, 0.0, 0.0], "test-model")
    db.commit()
    monkeypatch.setattr(
        "corpus_builder.embeddings.resolve_runtime_capability",
        lambda: SimpleNamespace(
            status="available",
            api_key=None,
            provider_id="openai_compat",
            base_url="http://127.0.0.1:1234/v1",
            reason="",
        ),
    )
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[1.0, 0.0, 0.0] for _ in texts],
    )

    results = semantic_search(db, "lokale embeddings", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key=None)

    assert results
    assert results[0].document_id == "doc_local"


def test_semantic_search_works_with_chunk_embeddings_only(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    json_path = make_input_pair("semantic_chunk_only", vision_structured, vision_report=vision_validation_report)
    assert load_from_file(db, json_path).status == "loaded"

    db.execute(
        "INSERT INTO embedding_chunks "
        "(chunk_id, document_id, chunk_index, chunk_type, page, source_kind, source_refs_json, chunk_text, vector, model, dimensions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "semantic_chunk_only::chunk::0000",
            "semantic_chunk_only",
            0,
            "free_text",
            1,
            "evidence_atoms",
            "[1]",
            "Typ: invoice | Titel: Ihre Schlussrechnung\n\nFreitext:\nSchlussrechnung fuer Stromlieferung an Norman Weiss.",
            struct.pack("3f", 1.0, 0.0, 0.0),
            "test-model",
            3,
            "2026-01-01T00:00:00Z",
        ),
    )
    db.commit()
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[1.0, 0.0, 0.0] for _ in texts],
    )

    results = semantic_search(db, "Schlussrechnung", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key="injected-secret")

    assert results
    assert results[0].document_id == "semantic_chunk_only"
    assert results[0].snippet is not None
    assert "Schlussrechnung" in results[0].snippet
