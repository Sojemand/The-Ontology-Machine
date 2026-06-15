from __future__ import annotations

import sys
from pathlib import Path

from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.types.adapter_results import AdapterCallResult


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent


def _adapter_kwargs(tmp_path: Path) -> dict:
    return {"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT}


def test_phase19_fixture_backed_smoke_covers_creation_batch_and_merge_paths(tmp_path: Path) -> None:
    workspace = WorkspaceAdapter(**_adapter_kwargs(tmp_path))
    semantic = SemanticReleaseAdapter(**_adapter_kwargs(tmp_path))
    batch = PipelineBatchAdapter(**_adapter_kwargs(tmp_path))
    merge = MergeAdapter(**_adapter_kwargs(tmp_path))

    artifact_root = tmp_path / "Artifact Tree"
    database_path = artifact_root / "Corpus" / "active.db"
    source_file = tmp_path / "source_a.pdf"
    source_file.write_bytes(b"pdf")

    prepared = workspace.prepare_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})
    validated = workspace.validate_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})
    staged_taxonomy = semantic.stage_taxonomy(
        {
            "semantic_release_path": str(artifact_root / "Semantic Release"),
            "update_state": {"schema_version": "kernel.create_taxonomy_update_state.input.v1", "taxonomy_id": "taxonomy_a", "taxonomy_core": {"codes": ["alpha"]}},
            "target_identity": {},
        }
    )
    staged_projection = semantic.stage_projections(
        {
            "semantic_release_path": str(artifact_root / "Semantic Release"),
            "taxonomy_ref": staged_taxonomy.to_dict()["output_refs"]["component_identity"],
            "update_state": {"schema_version": "kernel.create_projections_update_state.input.v1", "projection_ids": ["projection_a"], "projection_precursors": [{"projection_id": "projection_a"}], "semantic_binding": {"codes": ["alpha"]}},
            "target_identity": {},
        }
    )
    release_candidate = semantic.create_custom_semantic_release(
        {
            "staged_taxonomy_ref": {"component_identity": staged_taxonomy.to_dict()["output_refs"]["component_identity"]},
            "staged_projection_ref": {"component_identity": staged_projection.to_dict()["output_refs"]["component_identity"]},
            "semantic_release_folder": str(artifact_root / "Semantic Release"),
            "target_identity": {},
        }
    )
    created_manifest = batch.create_batch_manifest(
        {
            "workflow_run_id": "wr_phase19_smoke",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "batch_kind": "manual_ingest",
            "artifact_root": str(artifact_root),
            "active_database": {"database_path": str(database_path)},
            "semantic_release": {"semantic_release_id": release_candidate.to_dict()["output_refs"]["release_ref"]["release_id"], "semantic_release_version": "v1", "release_fingerprint": release_candidate.to_dict()["output_refs"]["release_ref"]["release_fingerprint"], "taxonomy_fingerprint": "fp_tax"},
            "active_projections": [{"projection_id": "projection_a", "projection_fingerprint": "fp_projection"}],
            "input_files": [{"source_path": str(source_file)}],
            "target_identity": {"artifact_root_path": str(artifact_root)},
        }
    )
    finalized_manifest = batch.finalize_batch_manifest(
        {
            "workflow_run_id": "wr_phase19_smoke",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "pending_manifest_ref": created_manifest.to_dict()["output_refs"]["pending_manifest_ref"],
            "artifact_root": str(artifact_root),
            "orchestrator_run_ref": {"run_id": "orch_run"},
            "corpus_load_refs": [],
            "output_artifacts": [],
            "materialized_records": [{"document_id": "doc_1", "record_id": "rec_1"}],
            "record_counts": {"documents": 1, "normalized_records": 1},
            "correlation_report": {"status": "ok", "checked_records": 1},
            "target_identity": {"artifact_root_path": str(artifact_root)},
        }
    )
    merge_preflight = merge.multi_source_merge_preflight(
        {
            "selection": {
                "merge_run_id": "merge_phase19",
                "target_artifact_root": str(artifact_root),
                "target_database_path": str(database_path),
                "source_databases": [
                    {
                        "source_database_id": "db_a",
                        "source_database_path": str(tmp_path / "db_a.db"),
                        "source_artifact_root": str(tmp_path / "source_a"),
                        "source_state": "empty",
                        "source_semantic_release_id": "release_a",
                        "source_semantic_release_version": "v1",
                        "source_release_fingerprint": "fp_a",
                    },
                    {
                        "source_database_id": "db_b",
                        "source_database_path": str(tmp_path / "db_b.db"),
                        "source_artifact_root": str(tmp_path / "source_b"),
                        "source_state": "empty",
                        "source_semantic_release_id": "release_b",
                        "source_semantic_release_version": "v1",
                        "source_release_fingerprint": "fp_b",
                    },
                ],
            }
        }
    )

    for result in (
        prepared,
        validated,
        staged_taxonomy,
        staged_projection,
        release_candidate,
        created_manifest,
        finalized_manifest,
        merge_preflight,
    ):
        assert isinstance(result, AdapterCallResult)
        assert result.status == "ok"
    assert prepared.to_dict()["target_identity_proof"]["artifact_root_path_hash"]
    assert staged_taxonomy.to_dict()["target_identity_proof"]["taxonomy_fingerprint"]
    assert staged_projection.to_dict()["target_identity_proof"]["projection_fingerprint"]
    assert created_manifest.to_dict()["target_identity_proof"]["pipeline_batch_id"] == "pbt_20260506010101_deadbeef_1"
    assert merge_preflight.to_dict()["target_identity_proof"]["source_database_ids"] == ["db_a", "db_b"]
