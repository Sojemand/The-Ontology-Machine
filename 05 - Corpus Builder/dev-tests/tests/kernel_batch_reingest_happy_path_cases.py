from __future__ import annotations

import re
from pathlib import Path

from corpus_builder.database import connect
from corpus_builder.pipeline_batches.cleanup_workflow import cleanup_pipeline_batch_materialization
from corpus_builder.pipeline_batches.originals import restore_pipeline_batch_originals
from corpus_builder.pipeline_batches.path_io import read_json
from corpus_builder.pipeline_batches.reingest_workflow import reingest_pipeline_batch
from corpus_builder.pipeline_batches.selection import extract_sample_files_for_reingest, inspect_latest_pipeline_batch
from corpus_builder.semantic_release.multi_source_merge_types import path_hash

from .kernel_batch_reingest_support import artifact_tree, final_manifest


def test_batch_reingest_services_cover_inspect_extract_restore_cleanup_and_reingest(tmp_path: Path) -> None:
    artifact_root = tmp_path / ("Artifact Tree " + ("nested_" * 4))
    artifact_tree(artifact_root)
    manifest_path = final_manifest(artifact_root)
    target_identity = {"artifact_root_path_hash": path_hash(artifact_root), "state_snapshot_id": "snapshot_batch"}

    inspected = inspect_latest_pipeline_batch({"artifact_root": str(artifact_root), "target_identity": target_identity})
    extracted = extract_sample_files_for_reingest(
        {
            "artifact_root": str(artifact_root),
            "sample_count": 1,
            "target_input_path": str(artifact_root / "Input"),
            "target_identity": target_identity,
        }
    )
    restored = restore_pipeline_batch_originals(
        {
            "artifact_root": str(artifact_root),
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "target_input_path": str(artifact_root / "Input"),
            "target_identity": target_identity,
        }
    )
    cleanup_plan = {
        "schema_version": "kernel.cleanup_reingest_plan.v1",
        "workflow_run_id": "wr_batch",
        "cleanup_plan_id": "cln_batch_001",
        "cleanup_scope": "selected_batch",
        "target_identity": target_identity,
        "state_snapshot_id": "snapshot_batch",
        "source_manifest_ref": {
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "manifest_fingerprint": "sha256:test",
        },
        "affected_records": [{"document_id": "doc_1", "record_id": "rec_1"}],
        "affected_artifacts": [{"artifact_path": "Documents/normalized/doc_1.json"}],
        "affected_embeddings": [],
        "original_refs_preserved": [{"original_ref": str(tmp_path / "source_a.pdf"), "preserved": True}],
        "requires_confirmation": True,
        "rollback_policy": "journaled_no_scope_broadening",
    }
    cleaned = cleanup_pipeline_batch_materialization(
        {
            "artifact_root": str(artifact_root),
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "cleanup_scope": "selected_batch",
            "destructive_plan_ref": cleanup_plan,
            "confirmation_receipt_ref": {
                "status": "confirmed",
                "confirmation_scope": "remove_ingested_sample_batch",
                "target_identity": target_identity,
                "state_snapshot_id": "snapshot_batch",
            },
            "target_identity": target_identity,
        }
    )
    reingested = reingest_pipeline_batch(
        {
            "artifact_root": str(artifact_root),
            "workflow_run_id": "wr_batch",
            "source_pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "source_manifest_ref": {
                "artifact_path": manifest_path.relative_to(artifact_root).as_posix(),
                "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
                "manifest_fingerprint": "sha256:test",
            },
            "input_refs": restored["output_refs"]["input_refs"],
            "new_pipeline_batch_id": "pbt_20260506020202_deadbeef_2",
            "semantic_release_ref": {"release_id": "release_a"},
            "kernel_continuation_proof": {
                "continuation_scope": "kernel_continuation_scoped",
                "target_identity": target_identity,
                "state_snapshot_id": "snapshot_batch",
                "source_manifest_fingerprint": "sha256:test",
            },
            "target_identity": target_identity,
        }
    )

    assert inspected["status"] == "ok"
    assert extracted["output_refs"]["selected_records"]
    selection_id = extracted["output_refs"]["sample_selection_id"]
    assert re.fullmatch(r"sample_selection_[0-9a-f]{8}_1_[0-9a-f]{8}", selection_id)
    selection_manifest_path = artifact_root / extracted["output_refs"]["sample_selection_manifest_ref"]["artifact_path"]
    assert read_json(selection_manifest_path)["sample_selection_id"] == selection_id
    assert extracted["output_refs"]["copied_input_refs"][0]["target_input_ref"].startswith("Input/")
    assert restored["output_refs"]["restored_count"] == 1
    assert restored["output_refs"]["source_cleanup_verified"] is True
    assert cleaned["output_refs"]["cleanup_journal_ref"]["artifact_path"]
    assert cleaned["output_refs"]["removed_record_refs"] == [{"document_id": "doc_1", "record_id": "rec_1"}]
    assert not (artifact_root / "Documents" / "normalized" / "doc_1.json").exists()
    cleanup_conn = connect(str(artifact_root / "Corpus" / "active.db"))
    try:
        assert cleanup_conn.execute("SELECT COUNT(*) FROM documents WHERE id = 'doc_1'").fetchone()[0] == 0
    finally:
        cleanup_conn.close()
    assert reingested["output_refs"]["handoff_owner_action"] == "pipeline_run"
    assert reingested["output_refs"]["input_refs"][0]["content_hash"] == "sha256:source_a"
