from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from orchestrator.workspace_domain.workflow import create_artifact_tree, validate_artifact_tree


def _create_request(root: Path) -> dict:
    payload = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "create_artifact_tree",
        "workflow_run_id": "wr_artifact_tree",
        "adapter_call_id": "adc_artifact_tree",
        "requested_at": "2026-05-06T00:00:00Z",
        "artifact_root_parent": str(root.parent),
        "artifact_root_name": root.name,
        "create_mode": "idempotent_create",
        "folder_contract_version": "kernel_artifact_tree.v1",
        "target_identity": {},
    }
    payload["request_fingerprint"] = _request_fingerprint(payload)
    return payload


def _validate_request(root: Path) -> dict:
    payload = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "validate_artifact_tree",
        "workflow_run_id": "wr_artifact_tree",
        "adapter_call_id": "adc_artifact_tree",
        "requested_at": "2026-05-06T00:00:00Z",
        "artifact_root_path": str(root),
        "folder_contract_version": "kernel_artifact_tree.v1",
        "target_identity": {},
        "return_unexpected_paths": True,
    }
    payload["request_fingerprint"] = _request_fingerprint(payload)
    return payload


def test_create_and_validate_kernel_artifact_tree(tmp_path: Path) -> None:
    root = tmp_path / "Artifact Tree"

    created = create_artifact_tree(_create_request(root))
    validated = validate_artifact_tree(_validate_request(root))

    assert created["status"] == "ok"
    assert created["output_refs"]["artifact_root_path"] == str(root.resolve(strict=False))
    assert Path(created["output_refs"]["semantic_release_path"]).is_dir()
    assert validated["status"] == "ok"
    assert validated["output_refs"]["is_valid"] is True
    assert validated["output_refs"]["missing_paths"] == []


def test_validate_kernel_artifact_tree_reports_missing_folder(tmp_path: Path) -> None:
    root = tmp_path / "Broken Tree"
    create_artifact_tree(_create_request(root))
    (root / "Semantic Release").rmdir()

    validated = validate_artifact_tree(_validate_request(root))

    assert validated["status"] == "ok"
    assert validated["output_refs"]["is_valid"] is False
    assert "Semantic Release" in validated["output_refs"]["missing_paths"]


def test_artifact_tree_contract_rejects_missing_request_fingerprint(tmp_path: Path) -> None:
    payload = _create_request(tmp_path / "Artifact Tree")
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        create_artifact_tree(payload)


def _request_fingerprint(payload: dict) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
