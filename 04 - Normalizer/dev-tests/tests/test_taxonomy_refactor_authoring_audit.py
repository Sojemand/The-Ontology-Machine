from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.edit_contract.describe_surfaces import describe_surfaces
from normalizer_vision.edit_contract.taxonomy_release_draft import load_release_copy
from normalizer_vision.edit_contract.write_surface import write_surface
from normalizer_vision.semantic_release import build_semantic_release


def test_taxonomy_release_draft_surface_points_at_artifact_tree_copy(tmp_project_root: Path) -> None:
    descriptors = {item["surface_id"]: item for item in describe_surfaces(tmp_project_root)}
    descriptor = descriptors["normalizer.taxonomy_release_draft"]

    assert descriptor["source_path"] == "Artifact Tree / Semantic Release/releases/*/release.json"
    assert descriptor["storage_kind"] == "semantic_release_copy"
    assert descriptor["drift_status"] == "working_copy"
    assert descriptor["editor_kind"] == "taxonomy_release_draft"

    for item in descriptors.values():
        source_path = str(item.get("source_path") or "")
        assert "config/normalizer_taxonomy." not in source_path
        assert source_path != "config/semantic_release.default.json"
        assert "config/taxonomy_sources/" not in source_path


def test_release_draft_write_leaves_origin_release_unchanged(tmp_project_root: Path) -> None:
    artifact_root = tmp_project_root / "Artifact Tree"
    source_path = artifact_root / "Semantic Release" / "releases" / "semantic_release.default" / "release.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps(build_semantic_release(tmp_project_root), indent=2), encoding="utf-8")
    source_before = source_path.read_text(encoding="utf-8")

    draft = load_release_copy(artifact_root, source_path)
    draft["release"]["release_version"] = "manual.audit.v1"
    written = write_surface("normalizer.taxonomy_release_draft", draft, module_root=tmp_project_root)

    written_path = Path(written["working_release_path"])
    assert source_path.read_text(encoding="utf-8") == source_before
    assert written_path.exists()
    assert written_path != source_path
    assert not any((tmp_project_root / "config").glob("normalizer_taxonomy.*.json"))
