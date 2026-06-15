"""CLI semantic release and rebuild cases for Corpus Builder Vision."""

from __future__ import annotations

import json
from types import SimpleNamespace

from corpus_builder.main import _run_merge_preflight, _run_rebuild, _run_semantic_load


def test_run_semantic_load_stages_release(tmp_path, capsys, monkeypatch):
    release_path = tmp_path / "semantic_release.json"
    release_path.write_text(
        json.dumps(
            {
                "release_id": "semantic_release.cli",
                "release_version": "1",
                "master_taxonomy_id": "master.default",
                "master_taxonomy_version": "1",
                "projection_ids": ["default"],
                "materialization_version": "1",
                "fingerprint": "sha256:cli",
                "master_taxonomy": {"entity_types": [], "promotion_slots": []},
                "projections": [],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    args = SimpleNamespace(
        release=str(release_path),
        corpus_db=str(tmp_path / "corpus.db"),
    )

    monkeypatch.setattr(
        "corpus_builder.main.load_semantic_release",
        lambda *_args, **_kwargs: {
            "release_id": "semantic_release.cli",
            "release_version": "1",
            "source_path": str(release_path),
            "release_path": str(tmp_path / "published.semantic_release.json"),
            "report_path": str(tmp_path / "semantic_release_report.json"),
        },
    )

    _run_semantic_load(args)

    out = capsys.readouterr().out
    assert "Geladen: semantic_release.cli 1" in out
    assert "noch nicht aktiv" in out


def test_run_rebuild_prints_release_and_counts(tmp_path, capsys, monkeypatch):
    args = SimpleNamespace(
        pipeline_root=str(tmp_path / "pipeline"),
        normalized_dir=None,
        structured_dir=None,
        validation_dir=None,
        corpus_db=str(tmp_path / "corpus.db"),
        keep_existing=False,
    )

    monkeypatch.setattr(
        "corpus_builder.main.build_rebuild_bundles_from_artifacts",
        lambda *_args, **_kwargs: {
            "normalized_dir": str(tmp_path / "pipeline" / "normalized"),
            "structured_dir": str(tmp_path / "pipeline" / "structured"),
            "validation_dir": str(tmp_path / "pipeline" / "validation"),
            "bundle_count": 3,
            "missing_structured_count": 0,
            "missing_validation_count": 1,
        },
    )
    monkeypatch.setattr(
        "corpus_builder.main.rebuild_corpus_from_artifacts",
        lambda *_args, **_kwargs: {
            "active_release_id": "semantic_release.cli",
            "active_release_version": "2",
            "active_release_path": str(tmp_path / "state" / "semantic_release.active.json"),
            "corpus_db_path": str(tmp_path / "corpus.db"),
            "result": SimpleNamespace(loaded=3, skipped=0, archived=0, errors=0),
        },
    )

    _run_rebuild(args)

    out = capsys.readouterr().out
    assert "Artefakte: 3 normalized" in out
    assert "Aktiver Release: semantic_release.cli 2" in out
    assert "Neu aufgebaut: 3 geladen" in out


def test_run_merge_preflight_prints_state(tmp_path, capsys, monkeypatch):
    args = SimpleNamespace(
        source_db=str(tmp_path / "source.corpus.db"),
        target_db=str(tmp_path / "target.corpus.db"),
    )

    monkeypatch.setattr(
        "corpus_builder.main.merge_preflight",
        lambda *_args, **_kwargs: {
            "source_db_path": str(tmp_path / "source.corpus.db"),
            "target_db_path": str(tmp_path / "target.corpus.db"),
            "master_taxonomy_release_id": "master.default@1",
            "blocked": False,
            "snapshot_risk_confirmation_required": True,
            "collision_resolution_required": False,
            "pending_interactions": [{}],
        },
    )

    _run_merge_preflight(args)

    out = capsys.readouterr().out
    assert f"Source DB: {tmp_path / 'source.corpus.db'}" in out
    assert "Snapshot confirmation required: True" in out
