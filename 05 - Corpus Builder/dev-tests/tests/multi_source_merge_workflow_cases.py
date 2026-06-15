from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.database import connect
from corpus_builder.orchestrator_contract.command_types import WriteMergeReconciliationManifestCommand
from corpus_builder.orchestrator_contract.workflow_suite_phase19 import handle_write_merge_reconciliation_manifest
from corpus_builder.semantic_release.multi_source_merge_backfill import backfill_sql_from_merge_artifacts
from corpus_builder.semantic_release.multi_source_merge_preflight import multi_source_merge_preflight
from corpus_builder.semantic_release.multi_source_merge_workflow import multi_source_merge_databases

from .multi_source_merge_support import load_artifact_json, selection, source_database


def test_multi_source_merge_services_cover_preflight_merge_and_backfill(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")
    source_database(artifact_root, "db_b", "source_doc_b", "sha256:content_b")

    preflight = multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "filled_sql_and_artifacts"})
    reconciled = handle_write_merge_reconciliation_manifest(
        WriteMergeReconciliationManifestCommand(
            payload={
                "merge_run_id": merge_selection["merge_run_id"],
                "selection": merge_selection,
                "collision_manifest": {"manifest_revision": 2, "manifest_fingerprint": "sha256:manifest"},
                "selected_resolutions": [{"collision_id": "collision_1", "selected_resolution": "source_a"}],
                "target_database_path": merge_selection["target_database_path"],
                "target_identity": {},
            }
        ),
        context=None,
    )
    backfilled = backfill_sql_from_merge_artifacts(
        {
            "artifact_root": str(artifact_root),
            "merge_run_id": merge_selection["merge_run_id"],
            "target_database_path": merge_selection["target_database_path"],
            "merge_id_map_ref": merged["output_refs"]["merge_id_map_ref"],
        }
    )

    assert preflight["status"] == "ok"
    assert preflight["output_refs"]["source_class"] == "filled"
    assert preflight["target_identity_proof"]["source_database_ids"] == ["db_a", "db_b"]
    assert preflight["target_identity_proof"]["target_database_path_hash"].startswith("sha256:")
    assert preflight["output_refs"]["collision_manifest_ref"]["artifact_path"].startswith("Documents/logs/merge_runs/merge_phase19/")
    id_map = load_artifact_json(artifact_root, merged["output_refs"]["merge_id_map_ref"])
    artifact_map = load_artifact_json(artifact_root, merged["output_refs"]["artifact_map_ref"])
    assert "id_map_mappings" not in merged["output_refs"]
    assert "artifact_path_mappings" not in merged["output_refs"]
    assert len(json.dumps(merged).encode("utf-8")) < 16 * 1024
    assert id_map["mappings"]
    assert {item["source_document_id"] for item in id_map["mappings"]} == {"source_doc_a", "source_doc_b"}
    assert not any(item["source_document_id"].startswith("src_doc_") for item in id_map["mappings"])
    assert merged["target_identity_proof"]["target_database_path_hash"].startswith("sha256:")
    assert artifact_map["mappings"]
    assert merged["output_refs"]["record_counts"]["documents"] == 2
    assert reconciled["output_refs"]["manifest_revision"] == 2
    assert reconciled["receipt_fields"]["owner_action"] == "write_merge_reconciliation_manifest"
    assert "backfilled_record_refs" not in backfilled["output_refs"]
    assert backfilled["output_refs"]["post_backfill_counts"]["records"] == len(id_map["mappings"])
    assert backfilled["target_identity_proof"]["database_path_hash"] == backfilled["target_identity_proof"]["target_database_path_hash"]
    assert backfilled["target_identity_proof"]["target_database_path_hash"].startswith("sha256:")

    collision_manifest_path = artifact_root / preflight["output_refs"]["collision_manifest_ref"]["artifact_path"]
    collision_manifest = json.loads(collision_manifest_path.read_text(encoding="utf-8"))
    assert collision_manifest["schema_version"] == "kernel.database_merge_collision_manifest.v1"
    assert collision_manifest["manifest_revision"] == 2
    assert collision_manifest["manifest_fingerprint"].startswith("sha256:")

    assert id_map["schema_version"] == "kernel.database_merge_id_map.v1"
    assert id_map["record_count"] == len(id_map["mappings"])

    target_conn = connect(merge_selection["target_database_path"])
    try:
        target_rows = target_conn.execute("SELECT id, file_path FROM documents ORDER BY id").fetchall()
        assert len(target_rows) == 2
        assert all(Path(row["file_path"]).exists() for row in target_rows)
        state_rows = target_conn.execute("SELECT document_id, source_mode FROM document_processing_state ORDER BY document_id").fetchall()
        assert [row["source_mode"] for row in state_rows] == ["merged", "merged"]
    finally:
        target_conn.close()
