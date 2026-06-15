"""Embedding validation and failure-path tests for Corpus Builder Vision."""

from __future__ import annotations

from corpus_builder.embeddings import cosine_search, embed_pending, get_embeddings_for_runtime, load_embedding, store_embedding
from corpus_builder.models import EmbeddingRuntimeSettings
from tests.fixtures.loader_io import load_input_file

RUNTIME_SETTINGS = EmbeddingRuntimeSettings(model="test-model")


def test_embed_pending_rejects_too_few_vectors_atomically(
    db,
    default_config,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    for doc_id in ("embed_short_a", "embed_short_b"):
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["file_path"] = f"C:/docs/{doc_id}.pdf"
        structured["source"]["content_hash"] = f"sha256:{doc_id}"
        assert load_input_file(
            db,
            make_input_pair(doc_id, structured, vision_report=vision_validation_report, normalized=vision_normalized),
        ).status == "loaded"

    default_config.embeddings.dimensions = 3
    default_config.embeddings.batch_size = 10
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3]],
    )

    count = embed_pending(db, default_config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    assert count == 0
    assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0] == 0


def test_embed_pending_rejects_too_many_vectors_atomically(
    db,
    default_config,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    assert load_input_file(
        db,
        make_input_pair("embed_extra", vision_structured, vision_report=vision_validation_report, normalized=vision_normalized),
    ).status == "loaded"

    default_config.embeddings.dimensions = 3
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    )

    count = embed_pending(db, default_config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    assert count == 0
    assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0] == 0


def test_embed_pending_rejects_wrong_dimensions(
    db,
    default_config,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    assert load_input_file(
        db,
        make_input_pair("embed_dim", vision_structured, vision_report=vision_validation_report, normalized=vision_normalized),
    ).status == "loaded"

    default_config.embeddings.dimensions = 4
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3] for _ in texts],
    )

    count = embed_pending(db, default_config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    assert count == 0
    assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0] == 0


def test_cosine_search_skips_dimension_mismatches(db):
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES ('doc_a', 'a.pdf', 'C:/docs/a.pdf', 'sha256:a', 'invoice', 'finance', 'de', 'm', 0.9, 'pass', '2026-01-01T00:00:00Z')"
    )
    db.execute(
        "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
        "VALUES ('doc_b', 'b.pdf', 'C:/docs/b.pdf', 'sha256:b', 'invoice', 'finance', 'de', 'm', 0.9, 'pass', '2026-01-01T00:00:00Z')"
    )
    store_embedding(db, "doc_a", "a", [1.0, 0.0, 0.0], "test-model")
    store_embedding(db, "doc_b", "b", [1.0, 0.0], "test-model")
    db.commit()

    results = cosine_search(db, [1.0, 0.0, 0.0], top_k=5)

    assert [result["document_id"] for result in results] == ["doc_a"]


def test_load_embedding_rejects_corrupt_blob():
    try:
        load_embedding(b"abc")
    except ValueError as exc:
        assert "BLOB" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected malformed embedding blob to fail")


def test_cosine_search_skips_corrupt_or_inconsistent_blob_rows(db):
    for doc_id in ("doc_ok", "doc_bad_blob", "doc_bad_dims"):
        db.execute(
            "INSERT INTO documents (id, file_name, file_path, content_hash, document_type, category, language, model, model_confidence, validator_status, loaded_at) "
            "VALUES (?, ?, ?, ?, 'invoice', 'finance', 'de', 'm', 0.9, 'pass', '2026-01-01T00:00:00Z')",
            (doc_id, f"{doc_id}.pdf", f"C:/docs/{doc_id}.pdf", f"sha256:{doc_id}"),
        )

    store_embedding(db, "doc_ok", "ok", [1.0, 0.0, 0.0], "test-model")
    db.execute(
        "INSERT INTO embeddings (document_id, embedding_text, vector, model, dimensions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("doc_bad_blob", "bad", b"abc", "test-model", 3, "2026-01-01T00:00:00Z"),
    )
    db.execute(
        "INSERT INTO embeddings (document_id, embedding_text, vector, model, dimensions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("doc_bad_dims", "bad-dims", b"\x00\x00\x80?\x00\x00\x00@", "test-model", 3, "2026-01-01T00:00:00Z"),
    )
    db.commit()

    results = cosine_search(db, [1.0, 0.0, 0.0], top_k=5)

    assert [result["document_id"] for result in results] == ["doc_ok"]


def test_api_embeddings_use_only_injected_api_key(monkeypatch):
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings",
        lambda texts, model, api_key=None: (
            seen.update({"texts": texts, "model": model, "api_key": api_key}) or [[0.1, 0.2, 0.3]]
        ),
    )

    vectors = get_embeddings_for_runtime(
        ["hello"],
        RUNTIME_SETTINGS,
        api_key="injected-secret",
    )

    assert vectors == [[0.1, 0.2, 0.3]]
    assert seen["model"] == "test-model"
    assert seen["api_key"] == "injected-secret"
