"""Regression tests that search paths stay blob-free with page images present."""

from __future__ import annotations

from pathlib import Path

from corpus_builder.embeddings import store_embedding
from corpus_builder.models import EmbeddingRuntimeSettings
from corpus_builder.search import fulltext_search, hybrid_search, semantic_search
from tests.fixtures.loader_io import load_input_file

RUNTIME_SETTINGS = EmbeddingRuntimeSettings(model="test-model")


def _image_dir(root: Path, payload: dict) -> Path:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    file_name = str(source.get("file_name") or Path(str(source.get("file_path") or "")).name)
    hash_text = str(source.get("content_hash") or "").removeprefix("sha256:")
    return root / f"{file_name.replace(' ', '_')}.{hash_text[:8]}"


def _trace_sql(db, operation):
    statements: list[str] = []
    db.set_trace_callback(statements.append)
    try:
        result = operation()
    finally:
        db.set_trace_callback(None)
    return result, [statement.lower() for statement in statements]


def test_search_paths_do_not_read_page_image_blobs(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    monkeypatch,
    tmp_path,
):
    page_root = tmp_path / "page_images"
    image_dir = _image_dir(page_root, vision_structured)
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / "page_001.jpg").write_bytes(b"blob-search")
    json_path = make_input_pair("blob_free_doc", vision_structured, vision_report=vision_validation_report)

    assert load_input_file(db, json_path, persist_page_images_in_db=True, page_images_dir=page_root).status == "loaded"
    store_embedding(db, "blob_free_doc", "embed", [1.0, 0.0, 0.0], "test-model")
    db.commit()
    monkeypatch.setattr(
        "corpus_builder.embeddings.get_embeddings_for_runtime",
        lambda texts, runtime_settings, api_key=None: [[1.0, 0.0, 0.0] for _ in texts],
    )

    fts_results, fts_sql = _trace_sql(db, lambda: fulltext_search(db, "Schlussrechnung", limit=5))
    semantic_results, semantic_sql = _trace_sql(
        db,
        lambda: semantic_search(db, "Schlussrechnung", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key="injected-secret"),
    )
    hybrid_results, hybrid_sql = _trace_sql(
        db,
        lambda: hybrid_search(db, "Schlussrechnung", top_k=5, runtime_settings=RUNTIME_SETTINGS, api_key="injected-secret"),
    )

    assert fts_results and semantic_results and hybrid_results
    assert not any("document_page_images" in sql or "image_blob" in sql for sql in [*fts_sql, *semantic_sql, *hybrid_sql])
