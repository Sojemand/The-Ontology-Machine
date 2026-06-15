from __future__ import annotations

from pathlib import Path

from corpus_builder.database_analysis.workflow import read_database_analysis_evidence
from corpus_builder.semantic_release.multi_source_merge_types import path_hash

from .database_analysis_evidence_reader_support import artifact_tree, database


def test_read_database_analysis_evidence_returns_real_coverage_and_query_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    artifact_tree(artifact_root)
    db_path = database(artifact_root)

    result = read_database_analysis_evidence(
        {
            "database_path": str(db_path),
            "database_path_hash": path_hash(db_path),
            "artifact_root": str(artifact_root),
            "active_release_ref": {"release_id": "release_a", "release_version": "v1", "release_fingerprint": "fp_release"},
            "release_materialization_refs": [{"artifact_path": "Documents/logs/materialization.json", "pipeline_batch_id": "pbt_20260506010101_deadbeef_1"}],
            "analysis_scope": "database_coverage",
            "target_identity": {
                "database_path_hash": path_hash(db_path),
                "artifact_root_path_hash": path_hash(artifact_root),
                "release_fingerprint": "fp_release",
            },
        }
    )

    assert result["status"] == "ok"
    assert result["output_refs"]["database_summary"]["row_count"] == 1
    assert result["output_refs"]["coverage_metrics"]["structured_payload_coverage"] == 1.0
    assert result["output_refs"]["classification_coverage"][0]["document_type"] == "invoice"
    assert result["output_refs"]["projection_coverage"][0]["projection_id"] == "projection_a"
    assert result["output_refs"]["field_coverage"]["document_promotions"]["coverage_ratio"] == 1.0
    assert result["output_refs"]["promotion_coverage"][0]["slot"] == "total_amount"
    assert result["output_refs"]["promotion_coverage"][0]["candidate_backed_count"] == 1
    assert result["output_refs"]["release_materialization"]["materialized_batches"][0]["pipeline_batch_id"] == "pbt_20260506010101_deadbeef_1"
    assert result["output_refs"]["affected_documents"][0]["document_id"] == "doc_1"
    assert {query["name"] for query in result["output_refs"]["query_manifest"]["queries"]} >= {"document_counts", "promotion_coverage"}
