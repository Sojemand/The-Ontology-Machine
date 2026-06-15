from __future__ import annotations

from corpus_builder.embeddings import embed_document

from .embeddings_workflow_support import RUNTIME_SETTINGS


def test_embed_document_returns_false_for_empty_curated_text(db, default_config):
    default_config.embeddings.dimensions = 3

    success = embed_document(
        db,
        "blank-doc",
        {"classification": {}, "context": {}, "content": {"fields": {}, "rows": [], "free_text": ""}},
        default_config.embeddings,
        RUNTIME_SETTINGS,
    )

    assert success is False
