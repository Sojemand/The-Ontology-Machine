from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


CLEANUP_TARGETABLE_BATCH_KINDS = (
    "sample_ingest",
    "reingest_selected_samples",
    "workflow_continuation_ingest",
)


def is_cleanup_targetable_batch(manifest: Mapping[str, Any]) -> bool:
    if manifest.get("batch_kind") not in CLEANUP_TARGETABLE_BATCH_KINDS:
        return False
    eligibility = manifest.get("cleanup_eligibility")
    if not isinstance(eligibility, Mapping):
        return False
    if eligibility.get("cleanup_scope") == "selected_batch":
        return bool(eligibility.get("is_cleanup_targetable"))
    if manifest.get("batch_kind") == "workflow_continuation_ingest":
        return False
    return bool(eligibility.get("is_cleanup_targetable"))


def destructive_confirmation_matches(
    confirmation: Mapping[str, Any] | None,
    *,
    target_identity: Mapping[str, Any],
    state_snapshot_id: str,
    confirmation_scope: str,
) -> tuple[bool, str]:
    if not isinstance(confirmation, Mapping):
        return False, "confirmation_missing"
    decision = confirmation.get("status") or confirmation.get("user_decision")
    if decision not in {"confirmed", "submitted", True}:
        return False, "confirmation_missing"
    if confirmation.get("confirmation_scope") not in {None, confirmation_scope}:
        return False, "confirmation_missing"
    confirmed_target = confirmation.get("confirmed_target_identity") or confirmation.get("target_identity")
    confirmed_snapshot = confirmation.get("confirmed_state_snapshot_identity") or confirmation.get("state_snapshot_id")
    if isinstance(confirmed_snapshot, Mapping):
        confirmed_snapshot = confirmed_snapshot.get("state_snapshot_id")
    if isinstance(confirmed_target, Mapping) and not _confirmed_target_matches(
        confirmed_target,
        target_identity=target_identity,
        confirmed_snapshot=str(confirmed_snapshot or ""),
        state_snapshot_id=state_snapshot_id,
    ):
        return False, "target_identity_changed"
    if confirmed_snapshot is not None and str(confirmed_snapshot) != state_snapshot_id:
        return False, "target_identity_changed"
    return True, ""


def _confirmed_target_matches(
    confirmed_target: Mapping[str, Any],
    *,
    target_identity: Mapping[str, Any],
    confirmed_snapshot: str,
    state_snapshot_id: str,
) -> bool:
    if dict(confirmed_target) == dict(target_identity):
        return True
    if not confirmed_snapshot or confirmed_snapshot != state_snapshot_id:
        return False
    return _without_state_snapshot_id(confirmed_target) == _without_state_snapshot_id(target_identity)


def _without_state_snapshot_id(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in dict(value).items() if key != "state_snapshot_id"}


def plan_input_collision(
    original_ref: Mapping[str, Any],
    existing_input_refs: Sequence[Mapping[str, Any]],
    *,
    prefix: str,
) -> dict[str, Any]:
    requested_name = str(original_ref.get("target_input_name") or original_ref.get("file_name") or "")
    requested_hash = str(original_ref.get("content_hash") or "")
    if not requested_name:
        return {"collision_policy": "input_collision_unresolved", "reason": "target_input_name_missing"}

    same_name = [item for item in existing_input_refs if str(item.get("file_name") or item.get("input_relative_path", "")).endswith(requested_name)]
    same_hash = [item for item in existing_input_refs if requested_hash and item.get("content_hash") == requested_hash]

    if same_name and same_name[0].get("content_hash") == requested_hash:
        return {
            "collision_policy": "same_hash_same_name",
            "destination_ref": dict(same_name[0]),
        }
    if same_hash:
        return {
            "collision_policy": "same_hash_different_name",
            "destination_ref": {**dict(same_hash[0]), "alias_for": requested_name},
        }
    if same_name:
        safe_name = PurePosixPath(requested_name).name
        return {
            "collision_policy": "same_name_different_hash",
            "destination_ref": {
                "file_name": f"{prefix}_{safe_name}",
                "content_hash": requested_hash,
            },
        }
    return {
        "collision_policy": "no_collision",
        "destination_ref": {
            "file_name": requested_name,
            "content_hash": requested_hash,
        },
    }


def affected_records_from_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = manifest.get("materialized_records", [])
    if not isinstance(records, list):
        return []
    affected: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record, Mapping):
            affected.append(
                {
                    "document_id": record.get("document_id", ""),
                    "record_id": record.get("record_id", ""),
                    "pipeline_batch_id": manifest.get("pipeline_batch_id", ""),
                }
            )
    return affected


def affected_records_from_selection(selection_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = selection_manifest.get("selected_records", [])
    if not isinstance(records, list):
        return []
    return [
        {
            "document_id": record.get("document_id", ""),
            "record_id": record.get("record_id", ""),
            "selection_id": selection_manifest.get("sample_selection_id", ""),
        }
        for record in records
        if isinstance(record, Mapping)
    ]
