from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import owner_ok, path_hash
from .manifest_reader import read_json
from .path_io import write_json
from .types import REINGEST_REQUEST_SCHEMA_VERSION


PIPELINE_BATCH_ID_RE = re.compile(r"^pbt_\d{14}_[0-9a-f]{8}_\d+$")


def reingest_pipeline_batch(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_root_text = str(payload.get("artifact_root") or "").strip()
    if not artifact_root_text:
        raise ValueError("artifact_root is required.")
    artifact_root = Path(artifact_root_text).resolve(strict=False)
    target_identity = _mapping(payload, "target_identity")
    _validate_target_identity(artifact_root, target_identity)

    source_manifest_ref = _mapping(payload, "source_manifest_ref")
    input_refs = [dict(item) for item in payload.get("input_refs", []) if isinstance(item, Mapping)]
    new_pipeline_batch_id = str(payload.get("new_pipeline_batch_id") or "").strip()
    semantic_release_ref = _mapping(payload, "semantic_release_ref")
    continuation_proof = _mapping(payload, "kernel_continuation_proof")
    source_pipeline_batch_id = str(payload.get("source_pipeline_batch_id") or source_manifest_ref.get("pipeline_batch_id") or "").strip()

    if not PIPELINE_BATCH_ID_RE.match(new_pipeline_batch_id):
        raise ValueError("new_batch_id_invalid: new_pipeline_batch_id must match the Phase 11 batch ID shape.")
    if new_pipeline_batch_id == source_pipeline_batch_id:
        raise ValueError("new_batch_id_invalid: reingest requires a fresh pipeline_batch_id.")
    if not input_refs:
        raise ValueError("input_refs_missing: reingest requires restored Input refs.")
    if not semantic_release_ref:
        raise ValueError("release_missing: reingest requires semantic_release_ref.")
    if continuation_proof.get("continuation_scope") != "kernel_continuation_scoped":
        raise ValueError("continuation_proof_missing: reingest requires Kernel-issued continuation scope.")

    source_manifest, manifest_path = _load_source_manifest(artifact_root, source_manifest_ref)
    _validate_continuation(continuation_proof, target_identity, source_manifest_ref)
    validated_input_refs = _validated_input_refs(artifact_root, input_refs)

    request_payload = {
        "schema_version": REINGEST_REQUEST_SCHEMA_VERSION,
        "workflow_run_id": str(payload.get("workflow_run_id") or "wr_phase19"),
        "source_pipeline_batch_id": source_pipeline_batch_id,
        "source_manifest_ref": {
            "pipeline_batch_id": source_pipeline_batch_id,
            "manifest_fingerprint": str(source_manifest.get("manifest_fingerprint") or source_manifest_ref.get("manifest_fingerprint") or ""),
            "artifact_path": manifest_path.relative_to(artifact_root).as_posix(),
        },
        "restored_input_refs": validated_input_refs,
        "new_pipeline_batch_id": new_pipeline_batch_id,
        "semantic_release_ref": semantic_release_ref,
        "target_identity": dict(target_identity),
        "owner_handoff_action": "pipeline_run",
    }
    request_path = artifact_root / "Documents" / "logs" / "pipeline_batches" / new_pipeline_batch_id / "reingest_pipeline_batch_request.json"
    write_json(request_path, request_payload)
    output = {
        "reingest_request_ref": {"artifact_path": request_path.relative_to(artifact_root).as_posix()},
        "new_pipeline_batch_id": new_pipeline_batch_id,
        "input_refs": validated_input_refs,
        "handoff_owner_action": "pipeline_run",
    }
    return owner_ok(
        owner_action="reingest_pipeline_batch",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=dict(target_identity, pipeline_batch_id=new_pipeline_batch_id),
        output_refs=output,
        receipt_fields={
            "owner_module": "05 - Corpus Builder",
            "owner_action": "reingest_pipeline_batch",
            "pipeline_batch_id": new_pipeline_batch_id,
        },
    )


def _load_source_manifest(artifact_root: Path, source_manifest_ref: Mapping[str, Any]) -> tuple[dict[str, Any], Path]:
    pipeline_batch_id = str(source_manifest_ref.get("pipeline_batch_id") or "").strip()
    if not pipeline_batch_id:
        raise ValueError("source_manifest_missing: source_manifest_ref.pipeline_batch_id is required.")
    artifact_path = str(source_manifest_ref.get("artifact_path") or "").strip()
    if artifact_path:
        manifest_path = (artifact_root / artifact_path).resolve(strict=False)
    else:
        manifest_path = (artifact_root / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "pipeline_batch_manifest.json").resolve(strict=False)
    try:
        manifest_path.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError("source_manifest_stale: source manifest ref escapes the active artifact tree.") from exc
    manifest = read_json(manifest_path)
    if str(manifest.get("pipeline_batch_id") or "") != pipeline_batch_id:
        raise ValueError("source_manifest_stale: source manifest pipeline_batch_id does not match the requested reingest source.")
    expected_fingerprint = str(source_manifest_ref.get("manifest_fingerprint") or "").strip()
    if expected_fingerprint and expected_fingerprint != str(manifest.get("manifest_fingerprint") or ""):
        raise ValueError("source_manifest_stale: source manifest fingerprint is stale.")
    return manifest, manifest_path


def _validate_continuation(
    continuation_proof: Mapping[str, Any],
    target_identity: Mapping[str, Any],
    source_manifest_ref: Mapping[str, Any],
) -> None:
    proof_target = continuation_proof.get("target_identity")
    if isinstance(proof_target, Mapping):
        for key in ("artifact_root_path_hash", "database_path_hash", "target_hash"):
            expected = target_identity.get(key)
            actual = proof_target.get(key)
            if expected and actual and actual != expected:
                raise ValueError("target_identity_changed: continuation target identity does not match the active target.")
    manifest_fingerprint = str(source_manifest_ref.get("manifest_fingerprint") or "").strip()
    if manifest_fingerprint and str(continuation_proof.get("source_manifest_fingerprint") or "").strip() != manifest_fingerprint:
        raise ValueError("source_manifest_stale: continuation proof carries a stale source manifest fingerprint.")
    expected_snapshot = str(target_identity.get("state_snapshot_id") or "").strip()
    actual_snapshot = str(continuation_proof.get("state_snapshot_id") or "").strip()
    if expected_snapshot and actual_snapshot and actual_snapshot != expected_snapshot:
        raise ValueError("target_identity_changed: continuation state snapshot does not match the active target.")


def _validated_input_refs(artifact_root: Path, input_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in input_refs:
        artifact_path = str(item.get("artifact_path") or item.get("target_input_ref") or item.get("input_relative_path") or "").strip()
        if not artifact_path:
            raise ValueError("input_refs_missing: each restored Input ref must include artifact_path or target_input_ref.")
        normalized = artifact_path.replace("\\", "/")
        if not normalized.startswith("Input/"):
            raise ValueError("input_refs_missing: restored Input refs must remain inside the active Artifact Tree Input folder.")
        resolved = (artifact_root / normalized).resolve(strict=False)
        try:
            resolved.relative_to(artifact_root)
        except ValueError as exc:
            raise ValueError("input_refs_missing: restored Input ref escapes the active artifact tree.") from exc
        if not resolved.exists():
            raise ValueError("input_refs_missing: restored Input ref does not exist on disk.")
        content_hash = str(item.get("content_hash") or "").strip()
        if not content_hash:
            raise ValueError("input_refs_missing: restored Input refs must carry content_hash fingerprints.")
        validated.append(
            {
                "artifact_path": normalized,
                "content_hash": content_hash,
                "size_bytes": int(item.get("size_bytes") or 0),
            }
        )
    return validated


def _validate_target_identity(artifact_root: Path, target_identity: Mapping[str, Any]) -> None:
    expected_hash = str(target_identity.get("artifact_root_path_hash") or "").strip()
    if expected_hash and expected_hash != path_hash(artifact_root):
        raise ValueError("target_identity_changed: artifact_root_path_hash does not match the active artifact root.")


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}
