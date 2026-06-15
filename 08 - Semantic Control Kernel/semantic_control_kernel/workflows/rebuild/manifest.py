from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.types.rebuild import DatabaseRebuildManifest
from semantic_control_kernel.validation.rebuild_validation import rebuild_manifest_fingerprint, validate_rebuild_manifest


def build_rebuild_manifest(
    *,
    rebuild_run_id: str,
    workflow_run_id: str,
    artifact_root: str,
    target_database_path: str,
    loaded_release: Mapping[str, Any],
    corpus_builder_run_ref: Mapping[str, Any],
    embedding_policy: str,
    embedding_result: str,
    activation_receipt_id: str,
    record_count: int,
    overwrite_receipt_id: str | None = None,
    adapter_call_refs: Sequence[Mapping[str, Any]] = (),
) -> DatabaseRebuildManifest:
    payload = {
        "schema_version": DatabaseRebuildManifest.SCHEMA_VERSION,
        "activation_receipt_id": activation_receipt_id,
        "artifact_root": artifact_root,
        "corpus_builder_run_ref": dict(corpus_builder_run_ref),
        "created_at": utc_iso(),
        "embedding_policy": embedding_policy,
        "embedding_result": embedding_result,
        "finalized_at": utc_iso(),
        "loaded_release_fingerprint": loaded_release["loaded_release_fingerprint"],
        "loaded_semantic_release_id": loaded_release["loaded_semantic_release_id"],
        "loaded_semantic_release_version": loaded_release["loaded_semantic_release_version"],
        "manifest_fingerprint": "",
        "rebuild_run_id": require_state_id("rebuild_run_id", rebuild_run_id),
        "record_count": int(record_count),
        "target_database_path": target_database_path,
        "workflow_run_id": workflow_run_id,
    }
    if overwrite_receipt_id:
        payload["overwrite_receipt_id"] = overwrite_receipt_id
    if adapter_call_refs:
        payload["adapter_call_refs"] = [dict(item) for item in adapter_call_refs]
    payload["manifest_fingerprint"] = rebuild_manifest_fingerprint(payload)
    validate_rebuild_manifest(payload)
    return DatabaseRebuildManifest(payload)


def write_rebuild_manifest(artifact_root: str | Path, rebuild_run_id: str, manifest: Mapping[str, Any]) -> str:
    path = Path(artifact_root) / "Documents" / "logs" / "rebuild_runs" / require_state_id("rebuild_run_id", rebuild_run_id) / "rebuild_manifest.json"
    atomic_write_json(path, dict(manifest))
    return str(path)
