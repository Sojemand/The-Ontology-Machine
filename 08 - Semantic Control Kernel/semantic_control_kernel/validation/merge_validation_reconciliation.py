from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.validation.merge_validation_common import require_fields


def normalize_selected_resolutions(selected_resolutions: object) -> dict[str, str]:
    if not isinstance(selected_resolutions, list):
        raise ValueError("selected_resolutions must be a list of resolution entries.")
    normalized: dict[str, str] = {}
    for index, item in enumerate(selected_resolutions):
        if not isinstance(item, Mapping):
            raise ValueError(f"selected_resolutions[{index}] must be an object.")
        collision_id = str(item.get("collision_id", "")).strip()
        selected_resolution = str(item.get("selected_resolution", "")).strip()
        if not collision_id or not selected_resolution:
            raise ValueError(f"selected_resolutions[{index}] requires collision_id and selected_resolution.")
        normalized[collision_id] = selected_resolution
    return normalized


def validate_reconciliation_receipt(receipt: Mapping[str, Any], *, manifest: Mapping[str, Any]) -> dict[str, str]:
    require_fields(receipt, RECEIPT_FIELDS, "kernel.database_merge_reconciliation_receipt.v1")
    if receipt.get("schema_version") != "kernel.database_merge_reconciliation_receipt.v1":
        raise ValueError("schema_version must be kernel.database_merge_reconciliation_receipt.v1.")
    if str(receipt.get("merge_run_id", "")) != str(manifest.get("merge_run_id", "")):
        raise ValueError("merge_run_id does not match the active merge manifest.")
    if int(receipt.get("manifest_revision_before", -1)) != int(manifest.get("manifest_revision", -2)):
        raise ValueError("manifest_revision_before does not match the active merge manifest revision.")
    _validate_target_identity(receipt.get("target_identity"), manifest)
    if str(receipt.get("result_status", "")) != "resolved":
        raise ValueError("result_status must be resolved before activation can continue.")
    _validate_collision_ref(receipt.get("collision_manifest_ref"), manifest)
    return normalize_selected_resolutions(receipt.get("selected_resolutions"))


def _validate_target_identity(target_identity: object, manifest: Mapping[str, Any]) -> None:
    if not isinstance(target_identity, Mapping):
        raise ValueError("target_identity must be an object.")
    if str(target_identity.get("lock_scope", "")) != "merge":
        raise ValueError("target_identity.lock_scope must be merge.")
    if str(target_identity.get("artifact_root_path_hash", "")) != path_hash(str(manifest.get("target_artifact_root", ""))):
        raise ValueError("target_identity artifact_root_path_hash does not match the active merge target.")
    if str(target_identity.get("database_path_hash", "")) != path_hash(str(manifest.get("target_database_path", ""))):
        raise ValueError("target_identity database_path_hash does not match the active merge target.")


def _validate_collision_ref(collision_ref: object, manifest: Mapping[str, Any]) -> None:
    if isinstance(collision_ref, Mapping):
        manifest_fingerprint = str(collision_ref.get("manifest_fingerprint", ""))
        if manifest_fingerprint and manifest_fingerprint != str(manifest.get("manifest_fingerprint", "")):
            raise ValueError("collision_manifest_ref does not match the active merge manifest fingerprint.")


RECEIPT_FIELDS = (
    "schema_version",
    "merge_run_id",
    "reconciliation_receipt_id",
    "collision_manifest_ref",
    "selected_resolutions",
    "target_identity",
    "state_snapshot_identity",
    "created_at",
    "manifest_revision_before",
    "manifest_revision_after",
    "updated_collision_manifest_ref",
    "result_status",
    "receipt_fingerprint",
)
