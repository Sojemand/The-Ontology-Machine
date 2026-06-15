from __future__ import annotations

import json

import pytest

from corpus_builder.semantic_release import (
    REQUIRED_RELEASE_KEYS,
    collect_semantic_status,
    inspect_release_application_compatibility,
    load_release_from_path,
    materialize_document_semantics,
    validate_payload_against_release,
)
from corpus_builder.services import apply_semantic_release, load_semantic_release
from .semantic_release_surface_support import PROJECT_ROOT, _customized_release, _make_context

def test_semantic_release_surface_exports_path_stable_entry_points() -> None:
    assert "fingerprint" in REQUIRED_RELEASE_KEYS
    assert callable(load_release_from_path)
    assert callable(validate_payload_against_release)
    assert callable(materialize_document_semantics)
    assert callable(inspect_release_application_compatibility)
    assert callable(collect_semantic_status)

def test_load_release_from_path_rejects_missing_required_keys(tmp_path: Path) -> None:
    release_path = tmp_path / "broken.semantic_release.json"
    release_path.write_text(json.dumps({"release_id": "broken"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Semantic Release unvollstaendig"):
        load_release_from_path(release_path)

def test_load_release_from_path_accepts_utf8_bom(tmp_path: Path) -> None:
    release_path = tmp_path / "bom.semantic_release.json"
    release_text = (PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8")
    release_path.write_text(release_text, encoding="utf-8-sig")

    release = load_release_from_path(release_path)

    assert release["release_id"] == "semantic_release.default"

def test_default_release_config_contains_dynamic_promotion_surface() -> None:
    release = load_release_from_path(PROJECT_ROOT / "config" / "semantic_release.default.json")
    runtime_assets = release["runtime_semantic_assets"]

    assert release["runtime_locale"] == "en"
    assert release["master_taxonomy"]["promotion_slots"]
    assert runtime_assets["promotion_slots"] == release["master_taxonomy"]["promotion_slots"]
    assert all(projection["promotion_rules"] for projection in release["projections"])
    assert all(projection["promotion_rules"] for projection in release["projection_catalog"]["projections"])
    assert all(projection["promotion_rules"] for projection in runtime_assets["projection_catalog"]["projections"])
    assert not release["analysis"]["issues"]

def test_load_semantic_release_can_skip_global_mirror_writes(tmp_path: Path) -> None:
    context = _make_context(tmp_path / "module")
    external_dir = tmp_path / "external"
    external_dir.mkdir(parents=True)
    release_text = (PROJECT_ROOT / "config" / "semantic_release.default.json").read_text(encoding="utf-8")
    release_path = external_dir / "semantic_release.default.json"
    release_path.write_text(release_text, encoding="utf-8")
    published_path = context.config_dir / "semantic_release.default.json"
    report_path = context.state_dir / "semantic_release_report.json"
    original_published = published_path.read_text(encoding="utf-8")

    loaded = load_semantic_release(
        context,
        release_path=release_path,
        corpus_db_path=context.output_dir / "missing.corpus.db",
        write_global_mirrors=False,
    )

    assert loaded["global_mirrors_written"] is False
    assert loaded["source_path"] == str(release_path)
    assert loaded["release_path"] == str(release_path)
    assert loaded["release_fingerprint"] == loaded["fingerprint"]
    assert loaded["published_release_path"] is None
    assert loaded["report_path"] is None
    assert published_path.read_text(encoding="utf-8") == original_published
    assert not report_path.exists()

def test_default_release_config_rejects_custom_global_mirror_writes_but_allows_local_load(tmp_path: Path) -> None:
    context = _make_context(tmp_path / "module")
    published_path = context.config_dir / "semantic_release.default.json"
    original_published = published_path.read_text(encoding="utf-8")
    custom_path = tmp_path / "custom.semantic_release.json"
    custom_release = _customized_release(json.loads(original_published))
    custom_path.write_text(json.dumps(custom_release, indent=2, ensure_ascii=False), encoding="utf-8")

    loaded = load_semantic_release(
        context,
        release_path=custom_path,
        corpus_db_path=context.output_dir / "custom.corpus.db",
        write_global_mirrors=False,
    )

    assert loaded["release_id"] == "custom.release.v1"
    assert loaded["global_mirrors_written"] is False
    assert published_path.read_text(encoding="utf-8") == original_published
    with pytest.raises(ValueError, match="Canonical Default Semantic Release is immutable"):
        load_semantic_release(
            context,
            release_path=custom_path,
            corpus_db_path=context.output_dir / "custom.corpus.db",
            write_global_mirrors=True,
        )
    assert published_path.read_text(encoding="utf-8") == original_published

def test_default_release_config_rejects_custom_global_activation_but_allows_local_activation(tmp_path: Path) -> None:
    context = _make_context(tmp_path / "module")
    published_path = context.config_dir / "semantic_release.default.json"
    original_published = published_path.read_text(encoding="utf-8")
    custom_path = tmp_path / "custom.semantic_release.json"
    custom_release = _customized_release(json.loads(original_published))
    custom_path.write_text(json.dumps(custom_release, indent=2, ensure_ascii=False), encoding="utf-8")

    applied = apply_semantic_release(
        context,
        release_path=custom_path,
        corpus_db_path=context.output_dir / "custom.corpus.db",
        write_global_mirrors=False,
    )

    assert applied["release_id"] == "custom.release.v1"
    assert applied["global_mirrors_written"] is False
    assert published_path.read_text(encoding="utf-8") == original_published
    with pytest.raises(ValueError, match="Canonical Default Semantic Release is immutable"):
        apply_semantic_release(
            context,
            release_path=custom_path,
            corpus_db_path=context.output_dir / "custom.corpus.db",
            write_global_mirrors=True,
        )
    assert published_path.read_text(encoding="utf-8") == original_published
