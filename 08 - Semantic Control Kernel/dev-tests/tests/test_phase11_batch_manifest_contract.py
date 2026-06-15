from __future__ import annotations

import pytest

from test_phase11_fakes import final_manifest_for, target_for

from semantic_control_kernel.validation.batch_validation import ManifestFingerprintError, MaterializationRefError, validate_pipeline_batch_manifest
from semantic_control_kernel.validation.contract_validation import EnumValidationError, MissingRequiredFieldError, UnknownFieldError


def test_final_manifest_full_field_set_and_fingerprint_validate(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))

    validate_pipeline_batch_manifest(manifest)

    assert set(manifest) == {
        "schema_version",
        "pipeline_batch_id",
        "workflow_run_id",
        "created_at",
        "finalized_at",
        "batch_kind",
        "batch_status",
        "active_database",
        "artifact_root",
        "semantic_release",
        "active_projections",
        "input_files",
        "owner_run_refs",
        "output_artifacts",
        "materialized_records",
        "record_counts",
        "cleanup_eligibility",
        "manifest_fingerprint",
    }


def test_manifest_enum_validation_rejects_unknown_batch_kind(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))
    manifest["batch_kind"] = "old_batch_kind"

    with pytest.raises(EnumValidationError):
        validate_pipeline_batch_manifest(manifest)


def test_manifest_nested_identity_validation_rejects_missing_release_field(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))
    del manifest["semantic_release"]["release_fingerprint"]

    with pytest.raises(MissingRequiredFieldError):
        validate_pipeline_batch_manifest(manifest)


def test_manifest_fingerprint_validation_rejects_mutation(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))
    manifest["record_counts"]["documents"] = 99

    with pytest.raises(ManifestFingerprintError):
        validate_pipeline_batch_manifest(manifest)


def test_manifest_unknown_top_level_field_is_rejected(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))
    manifest["legacy_cleanup_token"] = "forbidden"

    with pytest.raises(UnknownFieldError):
        validate_pipeline_batch_manifest(manifest)


def test_materialization_ref_must_match_batch_and_release_identity(tmp_path) -> None:
    manifest = final_manifest_for(target_for(tmp_path))
    manifest["materialized_records"][0]["record_semantic_materialization_ref"]["release_fingerprint"] = "sha256:other"
    from semantic_control_kernel.policy.batch_policy import with_manifest_fingerprint

    manifest = with_manifest_fingerprint(manifest)

    with pytest.raises(MaterializationRefError):
        validate_pipeline_batch_manifest(manifest)
