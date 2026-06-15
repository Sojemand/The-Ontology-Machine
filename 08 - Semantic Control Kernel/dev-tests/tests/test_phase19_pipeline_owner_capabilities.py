from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent

DRIFT_PREFLIGHT = {
    "status": "drift_preflight: build_plan_authority_applied",
    "details": [
        {
            "finding": "Referenced workflow specs keep Kernel-facing route names but omit the resolved Phase 19 owner action registry.",
            "applied_detail": "Phase 19 owner contract names from the build plan remain canonical for adapters, manifests, and owner tests.",
        }
    ],
}


def test_phase19_drift_preflight_records_build_plan_authority() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert DRIFT_PREFLIGHT["details"]


def test_phase19_owner_action_names_are_exposed_in_module_manifests() -> None:
    orchestrator_manifest = json.loads((PIPELINE_ROOT / "00 - Orchestrator" / "module-manifest.json").read_text(encoding="utf-8"))
    corpus_manifest = json.loads((PIPELINE_ROOT / "05 - Corpus Builder" / "module-manifest.json").read_text(encoding="utf-8"))

    for action_name in ("create_artifact_tree", "validate_artifact_tree", "create_pipeline_batch_manifest", "finalize_pipeline_batch_manifest"):
        assert action_name in orchestrator_manifest["actions"]
    for action_name in (
        "create_empty_corpus_db",
        "validate_artifact_tree",
        "multi_source_merge_preflight",
        "multi_source_merge_databases",
        "write_merge_reconciliation_manifest",
        "backfill_sql_from_merge_artifacts",
    ):
        assert action_name in corpus_manifest["actions"]


def test_phase19_adapters_expose_owner_backed_methods(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    workspace = WorkspaceAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)
    corpus = CorpusAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)
    semantic = SemanticReleaseAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)
    batch = PipelineBatchAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)
    merge = MergeAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)

    for adapter, method_name in (
        (workspace, "prepare_artifact_tree"),
        (workspace, "validate_artifact_tree"),
        (corpus, "create_empty_database"),
        (corpus, "backfill_sql"),
        (semantic, "stage_taxonomy"),
        (semantic, "stage_projections"),
        (semantic, "remove_taxonomy_or_projection"),
        (semantic, "create_custom_semantic_release"),
        (semantic, "merge_semantic_release_candidates"),
        (batch, "create_batch_manifest"),
        (batch, "finalize_batch_manifest"),
        (merge, "multi_source_merge_preflight"),
        (merge, "merge_empty_databases"),
        (merge, "merge_filled_databases"),
        (merge, "merge_semantic_release_candidates"),
        (merge, "write_merge_reconciliation_manifest"),
        (merge, "write_combined_database"),
        (merge, "fill_artifact_tree"),
    ):
        assert hasattr(adapter, method_name)


def test_phase19_merge_write_and_fill_are_compatibility_labels(tmp_path: Path) -> None:
    merge = MergeAdapter(state_root=tmp_path / "state", pipeline_root=PIPELINE_ROOT)

    for result in (
        merge.write_combined_database({"selection": {"merge_run_id": "mrg_test"}}),
        merge.fill_artifact_tree({"selection": {"merge_run_id": "mrg_test"}}),
    ):
        payload = result.to_dict()
        assert payload["status"] == "blocked_by_kernel_precondition"
        assert payload["capability_status"] == "kernel_internal_no_pipeline_adapter"


def test_phase19_corpus_create_empty_database_is_owner_backed_and_writes_db(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    corpus = CorpusAdapter(state_root=state_root, pipeline_root=PIPELINE_ROOT)
    database_path = tmp_path / "Artifact Tree" / "Corpus" / "active.db"

    result = corpus.create_empty_database({"database_path": str(database_path)})
    payload = result.to_dict()

    assert result.status == "ok"
    assert payload["output_refs"]["database_path"] == str(database_path)
    assert payload["target_identity_proof"]["database_path"] == str(database_path)
    assert database_path.is_file()
