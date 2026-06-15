from __future__ import annotations

from copy import deepcopy

from test_phase11_fakes import final_manifest_for, owner_output, target_for, with_bad_final_manifest
from semantic_control_kernel.workflows.pipeline_run.correlation import correlate_pipeline_outputs


def test_correlation_fails_when_record_materialization_ref_is_missing(tmp_path) -> None:
    target = target_for(tmp_path)
    final_manifest = final_manifest_for(target)
    del final_manifest["materialized_records"][0]["record_semantic_materialization_ref"]
    pending = {
        "workflow_run_id": final_manifest["workflow_run_id"],
        "pipeline_batch_id": final_manifest["pipeline_batch_id"],
        "semantic_release": target.semantic_release_manifest_ref(),
    }

    report = correlate_pipeline_outputs(
        pending_manifest=pending,
        final_manifest=final_manifest,
        owner_output=owner_output(),
    )

    assert report["manifest_eligible"] is False
    assert any(item["code"] == "materialization_provenance_missing" for item in report["mismatch_diagnostics"])


def test_correlation_fails_when_release_fingerprint_changes(tmp_path) -> None:
    target = target_for(tmp_path)
    final_manifest = final_manifest_for(target)

    def mutate(manifest):
        manifest["semantic_release"]["release_fingerprint"] = "sha256:other_release"
        for record in manifest["materialized_records"]:
            record["record_semantic_materialization_ref"]["release_fingerprint"] = "sha256:other_release"

    final_manifest = with_bad_final_manifest(final_manifest, mutate)
    pending = {
        "workflow_run_id": final_manifest["workflow_run_id"],
        "pipeline_batch_id": final_manifest["pipeline_batch_id"],
        "semantic_release": target.semantic_release_manifest_ref(),
    }

    report = correlate_pipeline_outputs(
        pending_manifest=pending,
        final_manifest=final_manifest,
        owner_output=deepcopy(owner_output()),
    )

    assert report["manifest_eligible"] is False
    assert any(item["code"] == "release_fingerprint_mismatch" for item in report["mismatch_diagnostics"])


def test_correlation_fails_when_output_artifact_is_outside_artifact_tree(tmp_path) -> None:
    target = target_for(tmp_path)
    final_manifest = final_manifest_for(target)
    final_manifest = with_bad_final_manifest(
        final_manifest,
        lambda manifest: manifest["output_artifacts"]["raw_extracts"].append({"artifact_path": "../outside.json"}),
    )
    pending = {
        "workflow_run_id": final_manifest["workflow_run_id"],
        "pipeline_batch_id": final_manifest["pipeline_batch_id"],
        "semantic_release": target.semantic_release_manifest_ref(),
    }

    report = correlate_pipeline_outputs(
        pending_manifest=pending,
        final_manifest=final_manifest,
        owner_output=owner_output(),
    )

    assert report["manifest_eligible"] is False
    assert any(item["code"] == "output_outside_artifact_tree" for item in report["mismatch_diagnostics"])
