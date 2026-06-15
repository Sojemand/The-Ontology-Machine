from __future__ import annotations

from corpus_builder.embeddings import embed_pending, embed_pending_result
from corpus_builder.models import load_config
from tests.fixtures.loader_io import load_input_file

from .embeddings_workflow_support import RUNTIME_SETTINGS
from .semantic_release_test_support import build_release_variant


def test_embed_pending_stores_vectors_and_respects_text_cap(
    db,
    default_config,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    json_path = make_input_pair("embed_doc", vision_structured, vision_report=vision_validation_report, normalized=vision_normalized)
    assert load_input_file(db, json_path, semantic_release=build_release_variant()).status == "loaded"

    default_config.embeddings.max_text_chars = 120
    default_config.embeddings.dimensions = 3
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3] for _ in texts],
    )

    result = embed_pending_result(db, default_config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    row = db.execute("SELECT embedding_text, dimensions FROM embeddings WHERE document_id = ?", ("embed_doc",)).fetchone()
    assert row["dimensions"] == 3
    assert len(row["embedding_text"]) <= 120
    assert "_source_refs" not in row["embedding_text"]
    chunk_rows = db.execute(
        "SELECT chunk_type, source_kind, chunk_text FROM embedding_chunks WHERE document_id = ? ORDER BY chunk_index",
        ("embed_doc",),
    ).fetchall()
    assert chunk_rows
    count = result.count
    assert count == 1 + len(chunk_rows)
    assert f"{count} Embeddings erzeugt" in str(result.reason)
    assert f"{len(chunk_rows)} Chunks" in str(result.reason)
    assert {"promotion", "free_text", "row", "field"} <= {row["chunk_type"] for row in chunk_rows}
    assert all(len(row["chunk_text"]) <= 120 for row in chunk_rows)
    assert all("_source_refs" not in row["chunk_text"] for row in chunk_rows)


def test_embed_pending_skips_archived_documents(
    db,
    default_config,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
):
    active = dict(vision_structured)
    active["source"] = dict(vision_structured["source"])
    active["source"]["file_path"] = "C:/docs/embed-active.pdf"
    active["source"]["content_hash"] = "sha256:embed-active"
    archived = dict(vision_structured)
    archived["source"] = dict(vision_structured["source"])
    archived["source"]["file_path"] = "C:/docs/embed-archived.pdf"
    archived["source"]["content_hash"] = "sha256:embed-archived"
    assert load_input_file(db, make_input_pair("embed_active", active, vision_report=vision_validation_report, normalized=vision_normalized)).status == "loaded"
    assert load_input_file(db, make_input_pair("embed_archived", archived, vision_report=vision_validation_report, normalized=vision_normalized)).status == "loaded"
    db.execute("UPDATE documents SET is_archived = 1 WHERE id = ?", ("embed_archived",))
    db.commit()

    default_config.embeddings.dimensions = 3
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3] for _ in texts],
    )

    count = embed_pending(db, default_config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    stored_ids = [row["document_id"] for row in db.execute("SELECT document_id FROM embeddings").fetchall()]
    assert stored_ids == ["embed_active"]
    chunk_ids = [
        row["document_id"]
        for row in db.execute("SELECT DISTINCT document_id FROM embedding_chunks ORDER BY document_id").fetchall()
    ]
    assert chunk_ids == ["embed_active"]
    assert count == 1 + db.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0]


def test_embed_pending_tolerates_string_config_values_from_loaded_config(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """{
  "database": {
    "corpus_db": "./output/corpus.db"
  },
  "embeddings": {
    "batch_size": "2",
    "dimensions": "3",
    "max_text_chars": "120"
  }
}""",
        encoding="utf-8",
    )
    config = load_config(config_path, module_root=tmp_path)

    assert load_input_file(
        db,
        make_input_pair("embed_config_strings", vision_structured, vision_report=vision_validation_report, normalized=vision_normalized),
    ).status == "loaded"

    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[0.1, 0.2, 0.3] for _ in texts],
    )

    count = embed_pending(db, config.embeddings, RUNTIME_SETTINGS, api_key="injected-secret")

    assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 1
    chunk_count = db.execute("SELECT COUNT(*) FROM embedding_chunks").fetchone()[0]
    assert chunk_count >= 1
    assert count == 1 + chunk_count
