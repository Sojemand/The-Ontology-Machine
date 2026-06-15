from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .cleanup_workflow_paths import _cleanup_plan_path, _load_json_ref, _mapping
from .cleanup_workflow_source import _source_records


PLAN_SCHEMA_VERSION = "kernel.cleanup_reingest_plan.v1"


def _load_cleanup_plan(payload: Mapping[str, Any], artifact_root: Path) -> dict[str, Any]:
    destructive_plan_ref = _mapping(payload, "destructive_plan_ref")
    if destructive_plan_ref.get("schema_version") == PLAN_SCHEMA_VERSION:
        plan = destructive_plan_ref
    else:
        plan = _load_json_ref(
            destructive_plan_ref,
            artifact_root,
            default_path=_cleanup_plan_path(artifact_root, str(destructive_plan_ref.get("cleanup_plan_id") or "")),
        )
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ValueError("destructive_plan_ref must resolve to kernel.cleanup_reingest_plan.v1.")
    if plan.get("cleanup_scope") not in {"selected_batch", "sample_selection"}:
        raise ValueError("records_not_isolated: cleanup plan cleanup_scope is invalid.")
    affected_records = plan.get("affected_records")
    if not isinstance(affected_records, list) or not affected_records:
        raise ValueError("records_not_isolated: cleanup plan affected_records must be non-empty.")
    return dict(plan)


def _load_confirmation(payload: Mapping[str, Any], artifact_root: Path) -> dict[str, Any]:
    confirmation_ref = _mapping(payload, "confirmation_receipt_ref")
    if not confirmation_ref:
        raise ValueError("confirmation_missing: confirmation_receipt_ref is required.")
    if confirmation_ref.get("confirmation_scope"):
        return confirmation_ref
    return _load_json_ref(confirmation_ref, artifact_root)


def _validate_confirmation(
    confirmation: Mapping[str, Any],
    target_identity: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    if str(confirmation.get("status") or "confirmed") not in {"confirmed", "ok"}:
        raise ValueError("confirmation_missing: destructive cleanup confirmation is not confirmed.")
    confirmed_target = confirmation.get("target_identity")
    if isinstance(confirmed_target, Mapping):
        for key in ("artifact_root_path_hash", "database_path_hash", "target_hash"):
            expected = target_identity.get(key)
            actual = confirmed_target.get(key)
            if expected and actual and actual != expected:
                raise ValueError("target_identity_changed: destructive confirmation target does not match request target.")
    plan_snapshot = str(plan.get("state_snapshot_id") or "")
    confirmation_snapshot = str(confirmation.get("state_snapshot_id") or "")
    if plan_snapshot and confirmation_snapshot and confirmation_snapshot != plan_snapshot:
        raise ValueError("target_identity_changed: destructive confirmation state snapshot does not match cleanup plan.")


def _validate_plan_against_source(plan: Mapping[str, Any], source_manifest: Mapping[str, Any]) -> None:
    expected = {_record_identity(item) for item in _source_records(source_manifest)}
    actual = {_record_identity(item) for item in plan.get("affected_records", []) if isinstance(item, Mapping)}
    if not expected or actual != expected:
        raise ValueError("records_not_isolated: cleanup plan does not match the isolated source records.")


def _record_identity(record: Mapping[str, Any]) -> tuple[str, str]:
    return str(record.get("document_id") or ""), str(record.get("record_id") or "")
