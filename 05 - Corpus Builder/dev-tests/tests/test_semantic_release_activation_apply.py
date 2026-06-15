from __future__ import annotations

import json

from corpus_builder.services import activation_preflight, apply_semantic_release, read_active_semantic_release
from .semantic_release_surface_support import _embedded_release_headers, _make_context, _refresh_release_fingerprint

def test_activation_preflight_allows_master_line_change_before_db_initialization(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    release = json.loads((context.config_dir / "semantic_release.default.json").read_text(encoding="utf-8"))
    release["master_taxonomy_release_id"] = "sha256:new-master-line"
    if isinstance(release.get("projection_catalog"), dict):
        release["projection_catalog"]["master_taxonomy_release_id"] = "sha256:new-master-line"
    if isinstance(release.get("runtime_semantic_assets"), dict):
        release["runtime_semantic_assets"]["master_taxonomy_release_id"] = "sha256:new-master-line"
        projection_catalog = release["runtime_semantic_assets"].get("projection_catalog")
        if isinstance(projection_catalog, dict):
            projection_catalog["master_taxonomy_release_id"] = "sha256:new-master-line"
    _refresh_release_fingerprint(release)
    release_path = context.output_dir / "semantic_release.new-master.json"
    release_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")

    preflight = activation_preflight(
        context,
        release_path=release_path,
        corpus_db_path=context.output_dir / "test.corpus.db",
    )

    assert preflight["initialization_required"] is True
    assert preflight["requires_confirmation"] is False
    assert preflight["next_snapshot"]["master_taxonomy_release_id"] == "sha256:new-master-line"

def test_apply_semantic_release_allows_snapshot_change_on_empty_db_without_confirmation(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    db_path = context.output_dir / "test.corpus.db"
    next_release = json.loads((context.config_dir / "semantic_release.default.json").read_text(encoding="utf-8"))
    next_release_path = context.output_dir / "semantic_release.next.json"
    next_release_path.write_text(json.dumps(next_release, indent=2, ensure_ascii=False), encoding="utf-8")
    initial_release = json.loads(json.dumps(next_release))
    initial_release["release_version"] = "initial.v1"
    for payload in _embedded_release_headers(initial_release):
        payload["release_version"] = initial_release["release_version"]
    _refresh_release_fingerprint(initial_release)
    initial_release_path = context.output_dir / "semantic_release.initial.json"
    initial_release_path.write_text(json.dumps(initial_release, indent=2, ensure_ascii=False), encoding="utf-8")
    apply_semantic_release(
        context,
        release_path=initial_release_path,
        corpus_db_path=db_path,
    )

    preflight = activation_preflight(
        context,
        release_path=next_release_path,
        corpus_db_path=db_path,
    )
    applied = apply_semantic_release(
        context,
        release_path=next_release_path,
        corpus_db_path=db_path,
    )
    active = read_active_semantic_release(context, corpus_db_path=db_path)

    assert preflight["db_changes"]["total_documents"] == 0
    assert preflight["requires_confirmation"] is False
    assert preflight["allowed_actions"] == ["cancel", "activate_only"]
    assert applied["no_op"] is False
    assert active["release"]["projection_ids"] == next_release["projection_ids"]

def test_apply_semantic_release_can_skip_global_mirror_writes(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    db_path = context.output_dir / "workspace.corpus.db"
    published_path = context.config_dir / "semantic_release.default.json"
    active_path = context.state_dir / "semantic_release.active.json"
    original_published = published_path.read_text(encoding="utf-8")
    original_active = active_path.read_text(encoding="utf-8")
    report_path = context.state_dir / "semantic_release_report.json"
    workspace_release = json.loads(original_published)
    release_path = context.output_dir / "workspace.semantic_release.json"
    release_path.write_text(json.dumps(workspace_release, indent=2, ensure_ascii=False), encoding="utf-8")

    applied = apply_semantic_release(
        context,
        release_path=release_path,
        corpus_db_path=db_path,
        write_global_mirrors=False,
    )
    active = read_active_semantic_release(context, corpus_db_path=db_path)

    assert applied["global_mirrors_written"] is False
    assert active["release"]["release_id"] == workspace_release["release_id"]
    assert published_path.read_text(encoding="utf-8") == original_published
    assert active_path.read_text(encoding="utf-8") == original_active
    assert applied["report_path"] is None
    assert not report_path.exists()
