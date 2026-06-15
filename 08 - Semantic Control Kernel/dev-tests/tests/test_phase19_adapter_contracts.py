from __future__ import annotations

import json

from phase19_adapter_unblock_support import (
    AdapterCallResult,
    _adapters,
    _request_fingerprint,
    _seed_analysis_database,
)

def test_phase19_valid_owner_payloads_no_longer_return_missing_capability(tmp_path: Path) -> None:
    workspace, corpus, semantic, batch, merge = _adapters(tmp_path)
    artifact_root = tmp_path / "Artifact Tree"
    database_path = artifact_root / "Corpus" / "active.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    _seed_analysis_database(artifact_root)
    semantic_release_path = artifact_root / "Semantic Release"
    source_file = tmp_path / "source_a.pdf"
    source_file.write_bytes(b"pdf")

    workspace_result = workspace.prepare_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})
    taxonomy_result = semantic.stage_taxonomy(
        {
            "semantic_release_path": str(semantic_release_path),
            "update_state": {"schema_version": "kernel.create_taxonomy_update_state.input.v1", "taxonomy_id": "taxonomy_a", "taxonomy_core": {"codes": ["alpha"]}},
            "target_identity": {},
        }
    )
    batch_result = batch.create_batch_manifest(
        {
            "workflow_run_id": "wr_phase19_unblock",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "batch_kind": "manual_ingest",
            "artifact_root": str(artifact_root),
            "active_database": {"database_path": str(database_path)},
            "semantic_release": {"semantic_release_id": "release_a", "semantic_release_version": "v1", "release_fingerprint": "fp_release", "taxonomy_fingerprint": "fp_tax"},
            "active_projections": [{"projection_id": "projection_a", "projection_fingerprint": "fp_projection"}],
            "input_files": [{"source_path": str(source_file)}],
            "target_identity": {"artifact_root_path": str(artifact_root)},
        }
    )
    merge_selection = {
        "merge_run_id": "merge_a",
        "target_artifact_root": str(artifact_root),
        "target_database_path": str(database_path),
        "source_databases": [
            {
                "source_database_id": "db_a",
                "source_database_path": str(tmp_path / "a.db"),
                "source_artifact_root": str(tmp_path / "a"),
                "source_state": "empty",
                "source_semantic_release_id": "release_a",
                "source_semantic_release_version": "v1",
                "source_release_fingerprint": "fp_a",
            },
            {
                "source_database_id": "db_b",
                "source_database_path": str(tmp_path / "b.db"),
                "source_artifact_root": str(tmp_path / "b"),
                "source_state": "empty",
                "source_semantic_release_id": "release_b",
                "source_semantic_release_version": "v1",
                "source_release_fingerprint": "fp_b",
            },
        ],
    }
    merge_result = merge.multi_source_merge_preflight({"selection": merge_selection})
    merge_write_result = merge.merge_empty_databases(
        {
            "selection": merge_selection,
            "collision_manifest_ref": merge_result.to_dict()["output_refs"]["collision_manifest_ref"],
        }
    )

    for result in (workspace_result, taxonomy_result, batch_result, merge_result, merge_write_result):
        assert isinstance(result, AdapterCallResult)
        assert result.status == "ok"
    assert workspace_result.to_dict()["target_identity_proof"]["artifact_root_path_hash"]
    assert taxonomy_result.to_dict()["target_identity_proof"]["artifact_root_path_hash"]
    assert taxonomy_result.to_dict()["target_identity_proof"]["taxonomy_fingerprint"]
    assert batch_result.to_dict()["target_identity_proof"]["pipeline_batch_id"] == "pbt_20260506010101_deadbeef_1"
    assert batch_result.to_dict()["target_identity_proof"]["database_path_hash"]
    assert batch_result.to_dict()["target_identity_proof"]["release_fingerprint"] == "fp_release"
    assert merge_result.to_dict()["target_identity_proof"]["source_database_ids"] == ["db_a", "db_b"]
    assert merge_result.to_dict()["target_identity_proof"]["target_database_path_hash"].startswith("sha256:")
    assert merge_write_result.to_dict()["target_identity_proof"]["source_database_ids"] == ["db_a", "db_b"]
    assert merge_write_result.to_dict()["target_identity_proof"]["target_database_path_hash"].startswith("sha256:")

def test_phase19_batch_adapter_translates_kernel_workflow_payloads_into_owner_contracts(tmp_path: Path) -> None:
    workspace, _corpus, _semantic, batch, _merge = _adapters(tmp_path)
    artifact_root = tmp_path / "Artifact Tree"
    database_path = artifact_root / "Corpus" / "active.db"
    source_file = tmp_path / "source_a.pdf"
    source_file.write_bytes(b"pdf")

    prepared = workspace.prepare_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})
    assert prepared.status == "ok"
    _seed_analysis_database(artifact_root)
    create_result = batch.create_batch_manifest(
        {
            "workflow_run_id": "wr_phase19_batch_contracts",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "batch_kind": "manual_ingest",
            "artifact_root": str(artifact_root),
            "active_database": {"database_path": str(database_path)},
            "semantic_release": {
                "semantic_release_id": "release_a",
                "semantic_release_version": "v1",
                "release_fingerprint": "fp_release",
                "taxonomy_fingerprint": "fp_tax",
            },
            "active_projections": [{"projection_id": "projection_a", "projection_fingerprint": "fp_projection"}],
            "input_files": [{"source_path": str(source_file), "content_hash": "sha256:source_a"}],
            "target_identity": {"artifact_root_path": str(artifact_root)},
        }
    )
    finalize_result = batch.finalize_batch_manifest(
        {
            "workflow_run_id": "wr_phase19_batch_contracts",
            "pipeline_batch_id": "pbt_20260506010101_deadbeef_1",
            "artifact_root": str(artifact_root),
            "pending_manifest_ref": create_result.to_dict()["output_refs"]["pending_manifest_ref"],
            "orchestrator_run_ref": {"run_id": "orch_phase19_batch_contracts"},
            "corpus_load_refs": [{"receipt_id": "corpus_load_phase19"}],
            "output_artifacts": {"documents": ["Documents/normalized/doc_1.json"]},
            "materialized_records": [{"document_id": "doc_1", "record_id": "rec_1"}],
            "record_counts": {"documents": 1},
            "correlation_report": {"status": "ok", "checked_records": 1},
            "target_identity": {"artifact_root_path": str(artifact_root)},
        }
    )
    assert create_result.status == "ok"
    assert finalize_result.status == "ok"
    assert create_result.to_dict()["target_identity_proof"]["pipeline_batch_id"] == "pbt_20260506010101_deadbeef_1"
    assert finalize_result.to_dict()["target_identity_proof"]["pipeline_batch_id"] == "pbt_20260506010101_deadbeef_1"

def test_phase19_incomplete_payloads_fail_closed_as_kernel_precondition_blockers(tmp_path: Path) -> None:
    workspace, corpus, semantic, batch, merge = _adapters(tmp_path)

    for result in (
        workspace.prepare_artifact_tree({}),
        corpus.create_empty_database({}),
        semantic.stage_taxonomy({}),
        batch.create_batch_manifest({}),
        merge.multi_source_merge_preflight({}),
    ):
        assert isinstance(result, AdapterCallResult)
        assert result.to_dict()["schema_version"] == "adapter.call_result.v1"
        assert result.to_dict()["status"] == "blocked_by_kernel_precondition"


def test_merge_preflight_uses_slow_machine_timeout(tmp_path: Path, monkeypatch) -> None:
    _workspace, _corpus, _semantic, _batch, merge = _adapters(tmp_path)
    captured: dict[str, object] = {}

    def fake_invoke(self, **kwargs):
        captured.update(kwargs)
        return self.ok_result(
            kernel_function=str(kwargs["kernel_function"]),
            capability_status=str(kwargs["capability_status"]),
        )

    monkeypatch.setattr(type(merge), "invoke", fake_invoke)

    result = merge.multi_source_merge_preflight(
        {
            "selection": {
                "merge_run_id": "merge_timeout_contract",
                "target_database_path": str(tmp_path / "target.db"),
                "source_databases": [{"source_database_id": "db_a"}],
            }
        }
    )

    assert result.status == "ok"
    assert captured["kernel_function"] == "database_merge_additive_only"
    assert captured["timeout_seconds"] == 1000
    assert captured["mutating"] is False


def test_filled_database_merge_uses_slow_machine_timeout(tmp_path: Path, monkeypatch) -> None:
    _workspace, _corpus, _semantic, _batch, merge = _adapters(tmp_path)
    captured: dict[str, object] = {}

    def fake_invoke(self, **kwargs):
        captured.update(kwargs)
        return self.ok_result(
            kernel_function=str(kwargs["kernel_function"]),
            capability_status=str(kwargs["capability_status"]),
        )

    monkeypatch.setattr(type(merge), "invoke", fake_invoke)

    result = merge.merge_filled_databases(
        {
            "selection": {
                "merge_run_id": "merge_timeout_contract",
                "target_database_path": str(tmp_path / "target.db"),
                "source_databases": [{"source_database_id": "db_a"}],
            }
        }
    )

    assert result.status == "ok"
    assert captured["owner_action"] == "multi_source_merge_databases"
    assert captured["kernel_function"] == "merge_database_filled_additive"
    assert captured["timeout_seconds"] == 1000
    assert captured["mutating"] is True


def test_phase19_owner_request_fingerprint_matches_written_request_payload(tmp_path: Path) -> None:
    workspace, _corpus, _semantic, _batch, _merge = _adapters(tmp_path)
    artifact_root = tmp_path / "Artifact Tree"

    result = workspace.prepare_artifact_tree({"artifact_root_path": str(artifact_root), "target_identity": {}})

    assert result.status == "ok"
    call_id = result.to_dict()["adapter_call_id"]
    request_path = tmp_path / "state" / "adapter_calls" / call_id / "request.json"
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))["request_payload"]

    assert request_payload["adapter_call_id"] == call_id
    assert request_payload["request_fingerprint"] == _request_fingerprint(request_payload)
