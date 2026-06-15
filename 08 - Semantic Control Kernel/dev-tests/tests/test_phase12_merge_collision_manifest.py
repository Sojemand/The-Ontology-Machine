from __future__ import annotations

import pytest

from semantic_control_kernel.validation.merge_validation import validate_collision_manifest
from semantic_control_kernel.workflows.merge.collision_manifest import activation_is_blocked, append_manifest_revision, build_collision_entry, build_collision_manifest


def _manifest(collisions=()):
    return build_collision_manifest(
        merge_run_id="merge_manifest",
        merge_route="filled_databases_merge_path",
        source_databases=[{"source_database_id": "source_db_a"}, {"source_database_id": "source_db_b"}],
        target_artifact_root="C:/target",
        target_database_path="C:/target/Corpus/corpus.db",
        collisions=collisions,
    ).to_dict()


def test_collision_manifest_required_fields_and_fingerprint() -> None:
    manifest = _manifest()

    validate_collision_manifest(manifest)
    assert manifest["schema_version"] == "kernel.database_merge_collision_manifest.v1"
    assert manifest["manifest_revision"] == 1


def test_append_only_revision_records_reconciled_collision() -> None:
    manifest = _manifest(
        [
            build_collision_entry(
                collision_id="col_semantic",
                collision_class="taxonomy_code_different_meaning",
                source_refs=[{"source_database_id": "source_db_a"}],
            )
        ]
    )
    revised = append_manifest_revision(
        manifest,
        selected_resolutions=[{"collision_id": "col_semantic", "selected_resolution": "rename_source_b"}],
    ).to_dict()

    assert manifest["manifest_revision"] == 1
    assert revised["manifest_revision"] == 2
    assert revised["collisions"][0]["resolution_status"] == "resolved"


def test_unresolved_collision_blocks_activation() -> None:
    manifest = _manifest(
        [
            build_collision_entry(
                collision_id="col_semantic",
                collision_class="projection_id_different_fingerprint",
                source_refs=[{"source_database_id": "source_db_a"}],
            )
        ]
    )

    assert activation_is_blocked(manifest)


def test_fingerprint_validation_rejects_silent_overwrite() -> None:
    manifest = _manifest()
    manifest["duplicate_policy"] = "mutated"

    with pytest.raises(ValueError, match="manifest_fingerprint"):
        validate_collision_manifest(manifest)
