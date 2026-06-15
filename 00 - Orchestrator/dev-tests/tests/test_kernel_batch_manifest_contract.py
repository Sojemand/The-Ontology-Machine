from __future__ import annotations

import hashlib
import json
import json as jsonlib
from pathlib import Path

import pytest

from orchestrator.pipeline_batches.workflow import create_pipeline_batch_manifest, finalize_pipeline_batch_manifest
from orchestrator.workspace_domain.workflow import create_artifact_tree


def _artifact_tree(root: Path) -> None:
    create_artifact_tree(
        _owner_request(
            "create_artifact_tree",
            artifact_root_parent=str(root.parent),
            artifact_root_name=root.name,
            create_mode="idempotent_create",
            folder_contract_version="kernel_artifact_tree.v1",
        )
    )


def _owner_request(owner_action: str, **fields: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": owner_action,
        "workflow_run_id": "wr_batch",
        "adapter_call_id": "adc_batch",
        "requested_at": "2026-05-06T00:00:00Z",
        "target_identity": {},
        **fields,
    }
    payload["request_fingerprint"] = _request_fingerprint(payload)
    return payload


def test_create_and_finalize_pipeline_batch_manifest(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    _artifact_tree(artifact_root)
    batch_id = "pbt_20260506010101_deadbeef_1"
    created = create_pipeline_batch_manifest(
        _owner_request(
            "create_pipeline_batch_manifest",
            pipeline_batch_id=batch_id,
            batch_kind="manual_ingest",
            active_database={"database_path": str(artifact_root / "Corpus" / "active.db")},
            artifact_root=str(artifact_root),
            semantic_release={"semantic_release_id": "release_a", "semantic_release_version": "v1", "release_fingerprint": "fp_release", "taxonomy_fingerprint": "fp_tax"},
            active_projections=[{"projection_id": "projection_a", "projection_fingerprint": "fp_projection"}],
            input_files=[{"source_path": str(tmp_path / "input_a.pdf")}],
            target_identity={"artifact_root_path": str(artifact_root)},
        )
    )
    finalized = finalize_pipeline_batch_manifest(
        _owner_request(
            "finalize_pipeline_batch_manifest",
            requested_at="2026-05-06T00:05:00Z",
            pipeline_batch_id=batch_id,
            pending_manifest_ref=created["output_refs"]["pending_manifest_ref"],
            orchestrator_run_ref={"run_id": "orch_run"},
            corpus_load_refs=[{"artifact_path": "load/report.json"}],
            output_artifacts=[{"artifact_path": "Documents/normalized/document.json"}],
            materialized_records=[{"document_id": "doc_1", "record_id": "rec_1"}],
            record_counts={"documents": 1, "normalized_records": 1},
            correlation_report={"artifact_path": "Documents/logs/correlation_report.json"},
            target_identity={"artifact_root_path": str(artifact_root)},
        )
    )

    manifest_path = artifact_root / finalized["output_refs"]["pipeline_batch_manifest_ref"]["artifact_path"]
    assert created["status"] == "ok"
    assert finalized["status"] == "ok"
    assert batch_id == created["output_refs"]["pipeline_batch_id"]
    assert created["target_identity_proof"]["database_path_hash"].startswith("sha256:")
    assert created["target_identity_proof"]["release_fingerprint"] == "fp_release"
    assert finalized["target_identity_proof"]["database_path_hash"].startswith("sha256:")
    assert finalized["output_refs"]["manifest_fingerprint"].startswith("sha256:")
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["batch_status"] == "finalized"
    assert "status" not in payload


def test_pipeline_batch_manifest_rejects_missing_request_fingerprint(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    _artifact_tree(artifact_root)
    payload = _owner_request(
        "create_pipeline_batch_manifest",
        pipeline_batch_id="pbt_20260506010101_deadbeef_1",
        batch_kind="manual_ingest",
        active_database={"database_path": str(artifact_root / "Corpus" / "active.db")},
        artifact_root=str(artifact_root),
        semantic_release={"semantic_release_id": "release_a", "semantic_release_version": "v1", "release_fingerprint": "fp_release"},
        active_projections=[],
        input_files=[],
    )
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        create_pipeline_batch_manifest(payload)  # type: ignore[arg-type]


def test_finalize_pipeline_batch_manifest_rejects_traversal_ref(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    _artifact_tree(artifact_root)
    outside_manifest = tmp_path / "outside.json"
    outside_manifest.write_text(json.dumps({"batch_status": "pending"}), encoding="utf-8")

    with pytest.raises(ValueError, match="traversal"):
        finalize_pipeline_batch_manifest(
            _owner_request(
                "finalize_pipeline_batch_manifest",
                pipeline_batch_id="pbt_20260506010101_deadbeef_1",
                pending_manifest_ref={"artifact_path": "../outside.json"},
                orchestrator_run_ref={"run_id": "orch_run"},
                corpus_load_refs=[],
                output_artifacts=[],
                materialized_records=[],
                record_counts={},
                correlation_report={},
                target_identity={"artifact_root_path": str(artifact_root)},
            )
        )

    assert outside_manifest.exists()


def test_finalize_pipeline_batch_manifest_rejects_wrong_in_root_ref(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    _artifact_tree(artifact_root)
    wrong_manifest = artifact_root / "Documents" / "logs" / "pipeline_batches" / "other" / "pending_pipeline_batch_manifest.json"
    wrong_manifest.parent.mkdir(parents=True)
    wrong_manifest.write_text(json.dumps({"batch_status": "pending"}), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match pipeline_batch_id"):
        finalize_pipeline_batch_manifest(
            _owner_request(
                "finalize_pipeline_batch_manifest",
                pipeline_batch_id="pbt_20260506010101_deadbeef_1",
                pending_manifest_ref={"artifact_path": "Documents/logs/pipeline_batches/other/pending_pipeline_batch_manifest.json"},
                orchestrator_run_ref={"run_id": "orch_run"},
                corpus_load_refs=[],
                output_artifacts=[],
                materialized_records=[],
                record_counts={},
                correlation_report={},
                target_identity={"artifact_root_path": str(artifact_root)},
            )
        )

    assert wrong_manifest.exists()


def _request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = jsonlib.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
