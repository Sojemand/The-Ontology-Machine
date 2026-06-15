from __future__ import annotations

import pytest

from semantic_control_kernel.policy.artifact_merge_policy import artifact_alias_allowed, missing_artifact_blocks, target_artifact_path
from semantic_control_kernel.workflows.merge.artifact_fill import plan_artifact_fill


def test_source_namespace_path_is_used_when_relative_path_collides() -> None:
    path = target_artifact_path(
        source_database_id="source_db_a",
        source_relative_path="Documents/originals/invoice.pdf",
        source_content_hash="sha256:a",
        existing_target_paths={"Documents/originals/invoice.pdf"},
    )

    assert path == "Documents/originals/source_db_a/invoice.pdf"


def test_same_name_same_hash_alias_is_allowed() -> None:
    assert artifact_alias_allowed(
        {"source_original_file_name": "invoice.pdf", "source_content_hash": "sha256:same"},
        {"source_original_file_name": "invoice.pdf", "source_content_hash": "sha256:same"},
    )


def test_same_name_different_hash_gets_deterministic_suffix_after_namespace_collision() -> None:
    path = target_artifact_path(
        source_database_id="source_db_a",
        source_relative_path="Documents/originals/invoice.pdf",
        source_content_hash="sha256:different",
        existing_target_paths={"Documents/originals/invoice.pdf", "Documents/originals/source_db_a/invoice.pdf"},
    )

    assert path.startswith("Documents/originals/source_db_a/invoice.")
    assert path.endswith(".pdf")


def test_missing_source_artifact_blocks_unless_owner_marks_optional() -> None:
    assert missing_artifact_blocks({})
    assert not missing_artifact_blocks({"owner_optional_artifact_proof": True})
    with pytest.raises(ValueError):
        plan_artifact_fill([{"source_database_id": "source_db_a", "source_content_hash": "sha256:a"}])
