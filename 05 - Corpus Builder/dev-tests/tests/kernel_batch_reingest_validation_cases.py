from __future__ import annotations

from pathlib import Path

import pytest

from corpus_builder.orchestrator_contract.validation_suite import parse_reingest_pipeline_batch_command
from corpus_builder.pipeline_batches.cleanup_workflow import cleanup_pipeline_batch_materialization
from corpus_builder.pipeline_batches.path_io import read_json, write_bytes, write_json
from corpus_builder.semantic_release.multi_source_merge_types import path_hash

from .kernel_batch_reingest_support import artifact_tree, final_manifest, link_or_skip, request_fingerprint


def test_cleanup_pipeline_batch_materialization_rejects_broadened_plan(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    artifact_tree(artifact_root)
    final_manifest(artifact_root)
    target_identity = {"artifact_root_path_hash": path_hash(artifact_root), "state_snapshot_id": "snapshot_batch"}

    with pytest.raises(ValueError, match="records_not_isolated"):
        cleanup_pipeline_batch_materialization(
            {
                "artifact_root": str(artifact_root),
                "destructive_plan_ref": {
                    "schema_version": "kernel.cleanup_reingest_plan.v1",
                    "workflow_run_id": "wr_batch",
                    "cleanup_plan_id": "cln_bad_001",
                    "cleanup_scope": "selected_batch",
                    "target_identity": target_identity,
                    "state_snapshot_id": "snapshot_batch",
                    "source_manifest_ref": {
                        "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
                        "manifest_fingerprint": "sha256:test",
                    },
                    "affected_records": [{"document_id": "doc_1", "record_id": "rec_1"}, {"document_id": "doc_2", "record_id": "rec_2"}],
                    "affected_artifacts": [{"artifact_path": "Documents/normalized/doc_1.json"}],
                    "affected_embeddings": [],
                    "original_refs_preserved": [],
                    "requires_confirmation": True,
                    "rollback_policy": "journaled_no_scope_broadening",
                },
                "confirmation_receipt_ref": {
                    "status": "confirmed",
                    "confirmation_scope": "remove_ingested_sample_batch",
                    "target_identity": target_identity,
                    "state_snapshot_id": "snapshot_batch",
                },
                "target_identity": target_identity,
            }
        )


def test_parse_reingest_pipeline_batch_requires_request_fingerprint() -> None:
    payload = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "reingest_pipeline_batch",
        "workflow_run_id": "wr_batch",
        "adapter_call_id": "adc_batch",
        "requested_at": "2026-05-07T00:00:00Z",
        "artifact_root": "C:/tmp/Artifact Tree",
        "source_manifest_ref": {"pipeline_batch_id": "pbt_20260506010101_deadbeef_1"},
        "input_refs": [{"artifact_path": "Input/doc_1.pdf", "content_hash": "sha256:doc_1"}],
        "new_pipeline_batch_id": "pbt_20260506020202_deadbeef_2",
        "semantic_release_ref": {"release_id": "release_a"},
        "kernel_continuation_proof": {"continuation_scope": "kernel_continuation_scoped"},
        "target_identity": {"artifact_root_path_hash": "sha256:test"},
    }
    payload["request_fingerprint"] = request_fingerprint(payload)
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        parse_reingest_pipeline_batch_command(payload)


def test_pipeline_batch_path_io_replaces_final_json_and_bytes(tmp_path: Path) -> None:
    json_path = tmp_path / "selection.json"
    json_path.write_text('{"old": true}', encoding="utf-8")
    json_alias = tmp_path / "selection.alias.json"
    link_or_skip(json_path, json_alias)

    write_json(json_path, {"new": True})

    assert read_json(json_path) == {"new": True}
    assert json_alias.read_text(encoding="utf-8") == '{"old": true}'

    bytes_path = tmp_path / "original.pdf"
    bytes_path.write_bytes(b"old")
    bytes_alias = tmp_path / "original.alias.pdf"
    link_or_skip(bytes_path, bytes_alias)

    write_bytes(bytes_path, b"new")

    assert bytes_path.read_bytes() == b"new"
    assert bytes_alias.read_bytes() == b"old"
