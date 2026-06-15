from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..workspace_domain.adapter import owner_response
from ..workspace_domain.policy import canonical_path, path_hash
from .manifest_policy import final_manifest_path, manifest_dir, manifest_fingerprint, pending_manifest_path
from .manifest_repository import read_json, write_json
from .types import PIPELINE_BATCH_MANIFEST_SCHEMA_VERSION
from .validation import validate_create_request, validate_finalize_request


def create_pipeline_batch_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    request = validate_create_request(payload)
    artifact_root_text = _required_path_text(request.get("artifact_root"), "artifact_root")
    artifact_root = canonical_path(artifact_root_text)
    pipeline_batch_id = str(request["pipeline_batch_id"])
    active_database = dict(request.get("active_database", {}))
    semantic_release = dict(request.get("semantic_release", {}))
    manifest_directory = manifest_dir(artifact_root, pipeline_batch_id)
    pending_path = pending_manifest_path(artifact_root, pipeline_batch_id)
    supplied_manifest = request.get("pending_manifest")
    manifest = dict(supplied_manifest) if isinstance(supplied_manifest, dict) else {
        "schema_version": PIPELINE_BATCH_MANIFEST_SCHEMA_VERSION,
        "pipeline_batch_id": pipeline_batch_id,
        "workflow_run_id": str(request["workflow_run_id"]),
        "batch_kind": str(request["batch_kind"]),
        "active_database": active_database,
        "artifact_root": artifact_root,
        "semantic_release": semantic_release,
        "active_projections": list(request.get("active_projections", [])),
        "input_files": list(request.get("input_files", [])),
        "batch_status": "pending",
        "materialized_records": [],
        "record_counts": {},
        "output_artifacts": [],
        "manifest_fingerprint": "",
    }
    seed = manifest_fingerprint(manifest)
    manifest["manifest_fingerprint"] = seed
    write_json(pending_path, manifest)
    output = {
        "pending_manifest_ref": {"artifact_path": pending_path.relative_to(Path(artifact_root)).as_posix()},
        "pipeline_batch_id": pipeline_batch_id,
        "manifest_directory": str(manifest_directory),
        "manifest_fingerprint_seed": seed,
        "owner_run_refs": {"pending_manifest_path": str(pending_path)},
    }
    target_identity = _mapping(request, "target_identity")
    artifact_hash = _identity_or_path_hash(target_identity, "artifact_root_path_hash", artifact_root)
    database_hash = _identity_or_path_hash(target_identity, "database_path_hash", str(active_database.get("database_path") or ""))
    return owner_response(
        owner_action="create_pipeline_batch_manifest",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=target_identity,
        output_refs=output,
        target_identity_proof={
            "artifact_root_path_hash": artifact_hash,
            "database_path_hash": database_hash,
            "pipeline_batch_id": pipeline_batch_id,
            "release_fingerprint": str(semantic_release.get("release_fingerprint") or ""),
        },
        receipt_fields={
            "owner_module": "00 - Orchestrator",
            "owner_action": "create_pipeline_batch_manifest",
            "artifact_root_path_hash": artifact_hash,
            "database_path_hash": database_hash,
            "pipeline_batch_id": pipeline_batch_id,
            "release_fingerprint": str(semantic_release.get("release_fingerprint") or ""),
            "manifest_fingerprint": seed,
        },
        summary="Pending pipeline batch manifest created.",
    )


def finalize_pipeline_batch_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    request = validate_finalize_request(payload)
    target_identity = _mapping(request, "target_identity")
    artifact_root_text = _required_path_text(
        target_identity.get("artifact_root_path") or target_identity.get("artifact_root"),
        "target_identity.artifact_root_path",
    )
    artifact_root = canonical_path(artifact_root_text)
    pipeline_batch_id = str(request["pipeline_batch_id"])
    pending_ref = _mapping(request, "pending_manifest_ref")
    pending_path = _pending_manifest_ref_path(artifact_root, pipeline_batch_id, pending_ref)
    manifest = read_json(pending_path)
    supplied_final = request.get("final_manifest")
    if isinstance(supplied_final, dict) and supplied_final:
        finalized = dict(supplied_final)
    else:
        finalized = dict(manifest)
        finalized.pop("status", None)
        finalized.update(
            {
                "batch_status": "finalized",
                "corpus_load_refs": list(request.get("corpus_load_refs", [])),
                "output_artifacts": _output_artifacts(request.get("output_artifacts", {})),
                "materialized_records": list(request.get("materialized_records", [])),
                "record_counts": dict(request.get("record_counts", {})),
                "correlation_report": dict(request.get("correlation_report", {})),
            }
        )
    finalized["manifest_fingerprint"] = manifest_fingerprint(finalized)
    final_path = final_manifest_path(artifact_root, pipeline_batch_id)
    write_json(final_path, finalized)
    if pending_path.exists():
        pending_path.unlink()
    output = {
        "pipeline_batch_manifest_ref": {"artifact_path": final_path.relative_to(Path(artifact_root)).as_posix()},
        "manifest_fingerprint": finalized["manifest_fingerprint"],
        "finalized_at": str(request.get("requested_at", "")),
        "cleanup_eligibility": {
            "can_restore_originals": True,
            "can_extract_samples": True,
            "can_cleanup_batch": True,
        },
        "correlation_report_ref": {"artifact_path": str((final_path.parent / "correlation_report.json").relative_to(Path(artifact_root)).as_posix())},
    }
    active_database = dict(manifest.get("active_database", {}))
    artifact_hash = _identity_or_path_hash(target_identity, "artifact_root_path_hash", artifact_root)
    database_hash = _identity_or_path_hash(target_identity, "database_path_hash", str(active_database.get("database_path") or ""))
    return owner_response(
        owner_action="finalize_pipeline_batch_manifest",
        capability="pipeline_batch_manifest_and_reingest_domain_service",
        target_identity=target_identity,
        output_refs=output,
        target_identity_proof={
            "artifact_root_path_hash": artifact_hash,
            "database_path_hash": database_hash,
            "pipeline_batch_id": pipeline_batch_id,
        },
        receipt_fields={
            "owner_module": "00 - Orchestrator",
            "owner_action": "finalize_pipeline_batch_manifest",
            "artifact_root_path_hash": artifact_hash,
            "database_path_hash": database_hash,
            "pipeline_batch_id": pipeline_batch_id,
            "manifest_fingerprint": finalized["manifest_fingerprint"],
        },
        summary="Pipeline batch manifest finalized.",
    )


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _output_artifacts(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return {"artifacts": list(value)}
    return {}


def _identity_or_path_hash(target_identity: dict[str, Any], key: str, path_value: str) -> str:
    value = target_identity.get(key)
    if isinstance(value, str) and value:
        return value
    return path_hash(path_value) if path_value else ""


def _required_path_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is missing or invalid.")
    return value.strip()


def _pending_manifest_ref_path(artifact_root: str, pipeline_batch_id: str, pending_ref: dict[str, Any]) -> Path:
    artifact_path = _artifact_relative_ref(pending_ref.get("artifact_path"), noun="pending_manifest_ref.artifact_path")
    root = Path(artifact_root).resolve(strict=False)
    candidate = (root / Path(artifact_path)).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("pending_manifest_ref.artifact_path must stay inside artifact_root.") from exc
    expected = pending_manifest_path(root, pipeline_batch_id).resolve(strict=False)
    if candidate != expected:
        raise ValueError("pending_manifest_ref.artifact_path does not match pipeline_batch_id.")
    return candidate


def _artifact_relative_ref(value: Any, *, noun: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{noun} is missing or invalid.")
    text = value.strip().replace("\\", "/")
    windows_ref = PureWindowsPath(text)
    posix_ref = PurePosixPath(text)
    if windows_ref.is_absolute() or windows_ref.drive or posix_ref.is_absolute():
        raise ValueError(f"{noun} must be relative to artifact_root.")
    if any(part in {"", ".", ".."} for part in posix_ref.parts):
        raise ValueError(f"{noun} must not contain traversal segments.")
    return text
