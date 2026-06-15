from __future__ import annotations

import json

from corpus_builder.database import connect
from corpus_builder.services import apply_semantic_release, merge_corpus_databases, merge_preflight, read_active_semantic_release
from corpus_builder.semantic_release.merge_preflight_helpers import pending_interactions
from .semantic_release_surface_support import _load_normalized, _make_context, _write_release_variant

def test_merge_preflight_allows_projection_drift_on_same_master_line(tmp_path: Path) -> None:
    source = _make_context(tmp_path / "source")
    target = _make_context(tmp_path / "target")
    source_db = source.output_dir / "test.corpus.db"
    target_db = target.output_dir / "test.corpus.db"

    apply_semantic_release(source, release_path=_write_release_variant(source, projection_ids=["housing.default.v1"]), corpus_db_path=source_db)
    apply_semantic_release(target, release_path=_write_release_variant(target), corpus_db_path=target_db)

    preflight = merge_preflight(target, source_db_path=source_db, target_db_path=target_db)

    assert preflight["blocked"] is False
    assert preflight["master_taxonomy_release_id"]
    assert preflight["source"]["active_snapshot"]["release"]["projection_ids"] != preflight["target"]["active_snapshot"]["release"]["projection_ids"]

def test_merge_preflight_blocks_different_master_lines(tmp_path: Path) -> None:
    source = _make_context(tmp_path / "source")
    target = _make_context(tmp_path / "target")
    source_db = source.output_dir / "test.corpus.db"
    target_db = target.output_dir / "test.corpus.db"

    apply_semantic_release(source, release_path=_write_release_variant(source, master_taxonomy_release_id="sha256:foreign-master-line"), corpus_db_path=source_db)
    apply_semantic_release(target, release_path=_write_release_variant(target), corpus_db_path=target_db)

    preflight = merge_preflight(target, source_db_path=source_db, target_db_path=target_db)

    assert preflight["blocked"] is True
    assert "master_taxonomy_release_id" in preflight["blocked_reason"]

def test_merge_corpus_databases_preserves_target_snapshot_on_snapshot_override(tmp_path: Path, vision_normalized) -> None:
    source = _make_context(tmp_path / "source")
    target = _make_context(tmp_path / "target")
    source_db = source.output_dir / "test.corpus.db"
    target_db = target.output_dir / "test.corpus.db"
    apply_semantic_release(source, release_path=_write_release_variant(source), corpus_db_path=source_db)
    apply_semantic_release(target, release_path=_write_release_variant(target), corpus_db_path=target_db)
    _load_normalized(source, source_db, vision_normalized, "source")
    _load_normalized(target, target_db, vision_normalized, "target")
    target_snapshot_id = read_active_semantic_release(target, corpus_db_path=target_db)["active_snapshot"]["snapshot_id"]
    conn = connect(str(source_db))
    try:
        conn.execute("UPDATE semantic_snapshots SET release_json = ? WHERE snapshot_id = ?", ("{broken", read_active_semantic_release(source, corpus_db_path=source_db)["active_snapshot"]["snapshot_id"]))
        conn.commit()
    finally:
        conn.close()

    preflight = merge_preflight(target, source_db_path=source_db, target_db_path=target_db)
    artifact_path = target.output_dir / "snapshot_risk_confirmation.json"
    artifact_path.write_text(json.dumps(preflight["pending_interactions"][0]["artifact_template"], indent=2, ensure_ascii=False), encoding="utf-8")
    merged = merge_corpus_databases(target, source_db_path=source_db, target_db_path=target_db, snapshot_risk_confirmation_artifact_path=artifact_path)

    assert preflight["snapshot_risk_confirmation_required"] is True
    assert merged["snapshot_risk_override_confirmed"] is True
    assert merged["active_snapshot_id"] == target_snapshot_id
    assert merged["integrity_status"] == "snapshot_override_confirmed"


def test_merge_preflight_recommended_confirmation_names_are_bounded(tmp_path: Path) -> None:
    source_path = tmp_path / (("source-corpus-with-a-very-long-name-" * 5) + ".db")
    target_path = tmp_path / (("target-corpus-with-a-very-long-name-" * 5) + ".db")

    interactions = pending_interactions(
        snapshot_risk=True,
        collisions=["doc-1"],
        collision_fingerprint="sha256:test",
        source_path=source_path,
        target_path=target_path,
        source_master="master.default",
        source_state={},
        target_state={},
        collision_allowed=True,
    )

    recommended_names = [item["recommended_filename"] for item in interactions]
    assert recommended_names
    assert all(len(name) <= 128 for name in recommended_names)
    assert all(name.endswith(".json") for name in recommended_names)
