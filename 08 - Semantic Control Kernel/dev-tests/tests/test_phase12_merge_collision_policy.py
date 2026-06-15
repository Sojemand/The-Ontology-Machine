from __future__ import annotations

from semantic_control_kernel.policy.merge_policy import COLLISION_POLICIES, DRIFT_PREFLIGHT, collision_policy
from semantic_control_kernel.workflows.merge.collision_manifest import build_collision_entry


EXPECTED_CLASSES = {
    "taxonomy_code_same_fingerprint",
    "taxonomy_code_different_meaning",
    "taxonomy_code_same_label_different_code",
    "projection_id_same_fingerprint",
    "projection_id_different_fingerprint",
    "projection_include_conflict",
    "document_content_hash_duplicate",
    "same_original_hash_different_file_name",
    "same_file_name_different_hash",
    "document_id_collision",
    "sql_primary_key_collision",
    "artifact_path_collision",
    "pipeline_batch_id_collision",
    "embedding_id_collision",
    "same_embedding_source_hash_different_embedding_model",
    "record_release_version_mixed",
}


def test_collision_policy_covers_every_phase12_class() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert {policy.collision_class for policy in COLLISION_POLICIES} == EXPECTED_CLASSES


def test_user_decision_flag_and_owner_function() -> None:
    policy = collision_policy("taxonomy_code_different_meaning")
    entry = build_collision_entry(
        collision_id="col_1",
        collision_class=policy.collision_class,
        source_refs=[{"source_database_id": "source_db_a"}],
    )

    assert entry["default_policy"] == "requires_reconcile"
    assert entry["requires_user_choice"] is True
    assert entry["resolution_owner"] == "kernel_dialog"
    assert entry["blocks_activation"] is True


def test_auto_policy_marks_non_user_collision_resolved() -> None:
    entry = build_collision_entry(
        collision_id="col_batch",
        collision_class="pipeline_batch_id_collision",
        source_refs=[{"source_database_id": "source_db_a"}],
    )

    assert entry["default_policy"] == "namespace with source database ID"
    assert entry["requires_user_choice"] is False
    assert entry["resolution_status"] == "resolved"
