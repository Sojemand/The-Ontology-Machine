from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from .services_artifact_rebuild_support import PROJECT_ROOT, write_active_release, write_default_config, write_json_artifact
from corpus_builder.context import ModuleContext
from corpus_builder.models import atomic_json_write
from corpus_builder.semantic_release import build_release_fingerprint
from corpus_builder.standalone_artifacts import rebuild_corpus_from_artifacts
from tests.semantic_release_test_support import build_release_variant


def test_rebuild_with_explicit_release_seeds_target_snapshot_not_global_active(
    tmp_path: Path,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    write_default_config(context)

    explicit_release = build_release_variant(
        project_root=PROJECT_ROOT,
        projection_ids=[vision_normalized["projection"]["projection_id"]],
    )
    explicit_release_path = tmp_path / "release.json"
    atomic_json_write(explicit_release_path, explicit_release)

    wrong_global_release = json.loads(json.dumps(explicit_release))
    wrong_global_release["master_taxonomy_id"] = "wrong.global.master"
    for projection in wrong_global_release["projections"]:
        projection["master_taxonomy_id"] = "wrong.global.master"
    wrong_global_release["fingerprint"] = build_release_fingerprint(wrong_global_release)
    wrong_global_release["release_fingerprint"] = wrong_global_release["fingerprint"]
    atomic_json_write(context.state_dir / "semantic_release.active.json", wrong_global_release)

    pipeline_root = tmp_path / "pipeline"
    write_json_artifact(pipeline_root / "normalized" / "invoice.pdf.structured.normalized.json", vision_normalized)

    db_path = tmp_path / "corpus.db"
    result = rebuild_corpus_from_artifacts(
        context,
        pipeline_root=pipeline_root,
        corpus_db_path=db_path,
        release_path=explicit_release_path,
        replace_existing=True,
    )

    assert result["seeded_release_snapshot"] is True
    assert result["result"].loaded == 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        state = conn.execute(
            "SELECT active_release_fingerprint FROM installation_state WHERE singleton = 1"
        ).fetchone()
        projection = conn.execute(
            "SELECT projection_json FROM document_payloads WHERE document_id = ?",
            ("invoice.pdf",),
        ).fetchone()
    finally:
        conn.close()
    assert state["active_release_fingerprint"] == explicit_release["fingerprint"]
    assert json.loads(projection["projection_json"])["master_taxonomy_id"] == explicit_release["master_taxonomy_id"]


def test_rebuild_corpus_from_artifacts_blocks_incompatible_projection_before_db_reset(
    tmp_path: Path,
    vision_normalized,
):
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    write_active_release(context)

    broken = dict(vision_normalized)
    broken["projection"] = dict(vision_normalized["projection"])
    broken["projection"]["projection_id"] = "missing.projection.v1"

    pipeline_root = tmp_path / "pipeline"
    write_json_artifact(pipeline_root / "normalized" / "broken.pdf.structured.normalized.json", broken)

    db_path = tmp_path / "corpus.db"
    db_path.write_text("keep-me", encoding="utf-8")

    with pytest.raises(ValueError, match="Rebuild abgebrochen"):
        rebuild_corpus_from_artifacts(
            context,
            pipeline_root=pipeline_root,
            corpus_db_path=db_path,
            replace_existing=True,
        )

    assert db_path.read_text(encoding="utf-8") == "keep-me"
