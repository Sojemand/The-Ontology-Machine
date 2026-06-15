from __future__ import annotations

from pathlib import Path
import sys

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.invocation import AdapterInvocation, OwnerBoundary, _derived_target_identity_proof
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.types.adapter_results import AdapterCallResult

from phase4_adapter_invocation_support import _invoke


def test_owner_target_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    result, _call_dir, _payload = _invoke(
        tmp_path,
        "success",
        extra_payload={"target_identity_proof": {"database_path_hash": "database_hash_other"}},
    )

    assert result.status == "target_identity_changed"
    assert result.to_dict()["diagnostics"][-1]["code"] == "target_identity_changed"


def test_semantic_merge_package_release_fingerprint_counts_as_target_proof() -> None:
    proof = _derived_target_identity_proof(
        {"merge_run_id": "mrg_test"},
        {
            "semantic_merge_package": {
                "release_fingerprint": "sha256:semantic_merge",
                "source_release_count": 2,
            }
        },
    )

    assert proof["merge_run_id"] == "mrg_test"
    assert proof["release_fingerprint"] == "sha256:semantic_merge"


def test_owner_backed_mutating_adapters_declare_required_target_identity_proof_fields(monkeypatch, tmp_path: Path) -> None:
    captured: list[AdapterInvocation] = []

    def fake_invoke(invocation: AdapterInvocation) -> AdapterCallResult:
        captured.append(invocation)
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_test",
                "adapter_name": invocation.boundary.adapter_name,
                "capability_status": invocation.boundary.capability_status,
                "diagnostics": [],
                "kernel_function": invocation.kernel_function,
                "output_refs": {},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    monkeypatch.setattr("semantic_control_kernel.adapters.base.invoke_owner_contract", fake_invoke)

    artifact_root = tmp_path / "Artifact Tree"
    semantic_release_path = artifact_root / "Semantic Release"
    database_path = artifact_root / "Corpus" / "active.db"

    WorkspaceAdapter(state_root=tmp_path / "state").prepare_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})
    SemanticReleaseAdapter(state_root=tmp_path / "state").stage_taxonomy(
        {
            "semantic_release_path": str(semantic_release_path),
            "update_state": {"schema_version": "kernel.create_taxonomy_update_state.input.v1", "taxonomy_id": "taxonomy_a"},
            "target_identity": {},
        }
    )
    PipelineBatchAdapter(state_root=tmp_path / "state").create_batch_manifest(
        {
            "workflow_run_id": "wr_phase4_batch",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "artifact_root": str(artifact_root),
            "active_database": {"database_path": str(database_path)},
            "semantic_release": {"release_fingerprint": "fp_release"},
            "input_files": [{"source_path": str(tmp_path / "source.pdf"), "source_hash": "sha256:source"}],
            "target_identity": {},
        }
    )
    CorpusAdapter(state_root=tmp_path / "state").backfill_sql(
        {
            "merge_run_id": "merge_123",
            "target_database_path": str(database_path),
            "artifact_root": str(artifact_root),
            "target_identity": {},
        }
    )

    assert [item.boundary.required_target_proof_fields for item in captured] == [
        ("artifact_root_path_hash",),
        ("artifact_root_path_hash", "taxonomy_fingerprint"),
        ("artifact_root_path_hash", "database_path_hash", "pipeline_batch_id", "release_fingerprint"),
        ("database_path_hash", "merge_run_id"),
    ]
    assert captured[0].target_identity["artifact_root_path_hash"]
    assert captured[1].target_identity["artifact_root_path_hash"]
    assert captured[2].target_identity["database_path_hash"]
    assert captured[2].target_identity["release_fingerprint"] == "fp_release"
    assert captured[3].target_identity["merge_run_id"] == "merge_123"
    assert captured[3].target_identity["database_path_hash"]
    assert captured[3].target_identity["target_database_path_hash"] == captured[3].target_identity["database_path_hash"]
    assert captured[3].request_payload["target_identity"]["database_path_hash"] == captured[3].target_identity["database_path_hash"]
    assert captured[3].request_payload["target_identity"]["target_database_path_hash"] == captured[3].target_identity["database_path_hash"]


def test_non_fake_owner_cannot_bypass_owner_runtime_with_python_override(tmp_path: Path) -> None:
    from semantic_control_kernel.adapters.invocation import invoke_owner_contract

    result = invoke_owner_contract(
        AdapterInvocation(
            state_root=tmp_path / "state",
            kernel_function="create_empty_database",
            boundary=OwnerBoundary(
                owner_module="05 - Corpus Builder",
                owner_module_root=tmp_path / "05 - Corpus Builder",
                owner_contract_module="corpus_builder.orchestrator_contract",
                owner_action="create_empty_corpus_db",
                adapter_name="CorpusAdapter",
                method_name="create_empty_database",
                capability_status="implemented_in_pipeline",
                timeout_seconds=5,
                mutating=True,
                required_target_proof_fields=("database_path|database_path_hash",),
                python_executable=Path(sys.executable),
            ),
            request_payload={"corpus_db_path": str(tmp_path / "corpus.db")},
            target_identity={"database_path_hash": "sha256:target"},
        )
    )

    diagnostics = result.to_dict()["diagnostics"]
    assert result.status == "owner_error"
    assert diagnostics[0]["code"] == "owner_runtime_missing"
