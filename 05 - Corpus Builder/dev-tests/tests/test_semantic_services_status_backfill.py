"""Semantic service status, audit, and backfill tests."""

from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.database import connect
from corpus_builder.services import (
    audit_semantics,
    backfill_semantics,
    build_load_bundle,
    load_batch,
    semantic_status,
)
from tests.fixtures.semantic_context import make_semantic_context


def test_build_load_bundle_accepts_normalized_only(tmp_path: Path):
    context = make_semantic_context(tmp_path)
    normalized_path = tmp_path / "sample.structured.normalized.json"
    normalized_path.write_text("{}", encoding="utf-8")

    bundle = build_load_bundle(
        context,
        normalized_path=normalized_path,
        corpus_db_path=tmp_path / "corpus.db",
    )

    assert bundle.normalized_path == normalized_path.resolve()
    assert bundle.structured_path is None
    assert bundle.validation_path is None
