from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.semantic_release.multi_source_merge_artifacts import copy_artifact_mappings
from corpus_builder.semantic_release.multi_source_merge_manifests import write_manifest

from .multi_source_merge_support import link_or_skip


def test_merge_manifest_write_replaces_final_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "merge_id_map.json"
    manifest_path.write_text('{"old": true}', encoding="utf-8")
    alias_path = tmp_path / "merge_id_map.alias.json"
    link_or_skip(manifest_path, alias_path)

    write_manifest(manifest_path, {"schema_version": "test.v1", "record_count": 1})

    assert json.loads(manifest_path.read_text(encoding="utf-8"))["schema_version"] == "test.v1"
    assert alias_path.read_text(encoding="utf-8") == '{"old": true}'


def test_merge_artifact_copy_replaces_final_path_without_mutating_hardlink_alias(tmp_path: Path) -> None:
    import hashlib

    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source = source_root / "Documents" / "originals" / "doc.pdf"
    target = target_root / "Documents" / "originals" / "doc.pdf"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_bytes(b"new-pdf")
    target.write_bytes(b"old-pdf")
    alias = tmp_path / "target-alias.pdf"
    link_or_skip(target, alias)

    report = copy_artifact_mappings(
        [
            {
                "source_path": str(source),
                "target_artifact_root": str(target_root),
                "target_artifact_path": "Documents/originals/doc.pdf",
            }
        ]
    )

    assert target.read_bytes() == b"new-pdf"
    assert alias.read_bytes() == b"old-pdf"
    assert report["copied_artifact_count"] == 1
    assert report["copied_artifact_mappings"][0]["target_sha256"] == "sha256:" + hashlib.sha256(b"new-pdf").hexdigest()
