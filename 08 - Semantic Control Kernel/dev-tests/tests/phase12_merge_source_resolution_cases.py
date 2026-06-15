from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from phase12_merge_entry_support import create_artifact_tree, write_release_package
from phase12_merge_source_support import seed_merge_source

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.merge.source_registry import resolve_merge_source_descriptors


def test_merge_source_resolution_finds_bound_db_below_artifact_tree_folder(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    container = tmp_path / "source_container"
    artifact_root = seed_merge_source(paths, container, "nested_source", release_version="3.0.0")

    descriptors = resolve_merge_source_descriptors(paths, [str(container)])

    assert len(descriptors) == 1
    assert descriptors[0]["source_artifact_root"] == str(artifact_root)
    assert descriptors[0]["source_database_path"] == str(artifact_root / "Corpus" / "corpus.db")
    assert descriptors[0]["source_semantic_release_version"] == "3.0.0"


def test_merge_source_resolution_uses_selected_artifact_tree_without_kernel_binding(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    artifact_root = tmp_path / "unbound_source"
    create_artifact_tree(artifact_root)
    write_release_package(
        artifact_root,
        release_id="unbound.release",
        release_version="4.0.0",
        release_fingerprint="sha256:unbound_release",
    )
    database_path = artifact_root / "Corpus" / "corpus.db"
    database_path.write_text("", encoding="utf-8")

    descriptors = resolve_merge_source_descriptors(paths, [str(artifact_root)])

    assert len(descriptors) == 1
    assert descriptors[0]["source_artifact_root"] == str(artifact_root)
    assert descriptors[0]["source_database_path"] == str(database_path)
    assert descriptors[0]["source_semantic_release_id"] == "unbound.release"
    assert descriptors[0]["source_semantic_release_version"] == "4.0.0"
    assert descriptors[0]["source_state"] == "empty"
    assert "durable_source_database_id" not in descriptors[0]
    assert list(paths.bindings_records_dir.glob("*.json")) == []
    assert list(paths.attach_states_by_database_dir.glob("*.json")) == []


def test_merge_source_resolution_derives_component_refs_from_live_release_package(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    artifact_root = tmp_path / "full_release_source"
    create_artifact_tree(artifact_root)
    release_path = artifact_root / "Semantic Release" / "releases" / "full.release"
    release_path.mkdir(parents=True, exist_ok=True)
    (release_path / "release.json").write_text(
        json.dumps(
            {
                "fingerprint": "sha256:full_release",
                "master_taxonomy": {
                    "field_codes": [{"code": "amount_due"}, {"code": "other"}],
                    "taxonomy_id": "taxonomy.full",
                    "taxonomy_version": "v1",
                },
                "master_taxonomy_id": "taxonomy.full",
                "master_taxonomy_release_id": "sha256:taxonomy_full",
                "master_taxonomy_version": "v1",
                "projection_ids": ["projection.full"],
                "projections": [
                    {
                        "include_field_codes": ["amount_due", "other"],
                        "projection_fingerprint": "sha256:projection_full",
                        "projection_id": "projection.full",
                    }
                ],
                "release_id": "full.release",
                "release_version": "v1",
                "runtime_locale": "en",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_root / "Corpus" / "corpus.db").write_text("", encoding="utf-8")

    descriptors = resolve_merge_source_descriptors(paths, [str(artifact_root)])

    release_ref = descriptors[0]["source_release_ref"]
    assert release_ref["taxonomy_ref"]["taxonomy_fingerprint"] == "sha256:taxonomy_full"
    assert release_ref["taxonomy_ref"]["master_taxonomy"]["field_codes"][0]["code"] == "amount_due"
    assert release_ref["projection_refs"][0]["projection_id"] == "projection.full"
    assert release_ref["projection_refs"][0]["projection_payload"]["projection_fingerprint"] == "sha256:projection_full"


def test_merge_source_resolution_classifies_sqlite_content_as_filled_without_manifest(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    artifact_root = tmp_path / "sqlite_source"
    create_artifact_tree(artifact_root)
    write_release_package(
        artifact_root,
        release_id="sqlite.release",
        release_version="5.0.0",
        release_fingerprint="sha256:sqlite_release",
    )
    database_path = artifact_root / "Corpus" / "corpus.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("create table documents (document_id text primary key)")
        connection.execute("insert into documents (document_id) values ('doc_001')")

    descriptors = resolve_merge_source_descriptors(paths, [str(artifact_root)])

    assert descriptors[0]["source_state"] == "filled"


def test_merge_source_resolution_treats_release_snapshot_only_database_as_empty(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    artifact_root = tmp_path / "snapshot_only_source"
    create_artifact_tree(artifact_root)
    write_release_package(
        artifact_root,
        release_id="snapshot.release",
        release_version="5.0.0",
        release_fingerprint="sha256:snapshot_release",
    )
    database_path = artifact_root / "Corpus" / "corpus.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("create table documents (document_id text primary key)")
        connection.execute("create table semantic_snapshots (snapshot_id text primary key)")
        connection.execute("insert into semantic_snapshots (snapshot_id) values ('active_release')")

    descriptors = resolve_merge_source_descriptors(paths, [str(artifact_root)])

    assert descriptors[0]["source_state"] == "empty"


def test_merge_source_resolution_prefers_single_non_default_live_release(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    artifact_root = tmp_path / "multi_release_source"
    create_artifact_tree(artifact_root)
    write_release_package(
        artifact_root,
        release_id="semantic_release.default",
        release_version="2026-03-28.v6",
        release_fingerprint="sha256:default_release",
    )
    write_release_package(
        artifact_root,
        release_id="custom.release",
        release_version="phase19.candidate",
        release_fingerprint="sha256:custom_release",
    )
    (artifact_root / "Corpus" / "corpus.db").write_text("", encoding="utf-8")

    descriptors = resolve_merge_source_descriptors(paths, [str(artifact_root)])

    assert descriptors[0]["source_semantic_release_id"] == "custom.release"
    assert descriptors[0]["source_semantic_release_version"] == "phase19.candidate"
