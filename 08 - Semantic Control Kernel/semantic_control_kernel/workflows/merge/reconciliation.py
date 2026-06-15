from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.validation.merge_validation import validate_reconciliation_receipt
from semantic_control_kernel.workflows.merge.collision_manifest import activation_is_blocked, append_manifest_revision
from semantic_control_kernel.workflows.merge.receipts import blocker_from_adapter_result


def reconcile_merged_semantic_release(
    merge_adapter: object,
    manifest: Mapping[str, Any],
    *,
    reconciliation_receipt: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, MergeWorkflowBlocker | None]:
    return _reconcile(
        merge_adapter,
        manifest,
        function_name="reconcile_merged_semantic_release",
        reconciliation_receipt=reconciliation_receipt,
    )


def reconcile_merged_database(
    merge_adapter: object,
    manifest: Mapping[str, Any],
    *,
    reconciliation_receipt: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, MergeWorkflowBlocker | None]:
    return _reconcile(
        merge_adapter,
        manifest,
        function_name="reconcile_merged_database",
        reconciliation_receipt=reconciliation_receipt,
    )


def _reconcile(
    merge_adapter: object,
    manifest: Mapping[str, Any],
    *,
    function_name: str,
    reconciliation_receipt: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, MergeWorkflowBlocker | None]:
    if activation_is_blocked(manifest):
        if not reconciliation_receipt:
            return None, MergeWorkflowBlocker(
                blocker_code="merge_collision_unresolved",
                step_id="awaiting_reconciliation",
                function_or_route=function_name,
                recovery_state_class="unresolved_merge_collision",
                user_visible_summary="Merge activation is blocked until Kernel reconciliation receives a valid receipt.",
            )
        try:
            selected_resolutions = validate_reconciliation_receipt(reconciliation_receipt, manifest=manifest)
        except ValueError as exc:
            detail = str(exc)
            recovery_state = "target_identity_changed" if "target_identity" in detail else "unresolved_merge_collision"
            blocker_code = "target_identity_changed" if recovery_state == "target_identity_changed" else "merge_reconciliation_receipt_invalid"
            return None, MergeWorkflowBlocker(
                blocker_code=blocker_code,
                step_id="awaiting_reconciliation",
                function_or_route=function_name,
                recovery_state_class=recovery_state,
                user_visible_summary="Merge reconciliation receipt no longer matches the active collision manifest.",
                diagnostics=({"reason": detail},),
            )
        resolved = append_manifest_revision(
            manifest,
            selected_resolutions=selected_resolutions,
        ).to_dict()
    else:
        resolved = dict(manifest)
    result = merge_adapter.write_merge_reconciliation_manifest(
        _owner_reconciliation_payload(
            manifest,
            resolved,
            reconciliation_receipt=reconciliation_receipt,
        )
    )
    blocker = blocker_from_adapter_result("awaiting_reconciliation", result, function_name=function_name)
    if blocker is not None:
        return None, blocker
    return resolved, None


def _owner_reconciliation_payload(
    manifest: Mapping[str, Any],
    resolved_manifest: Mapping[str, Any],
    *,
    reconciliation_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merge_run_id = str(manifest.get("merge_run_id", ""))
    payload: dict[str, Any] = {
        "collision_manifest": dict(resolved_manifest),
        "merge_run_id": merge_run_id,
        "selected_resolutions": _selected_resolution_entries(reconciliation_receipt),
        "target_artifact_root": str(manifest.get("target_artifact_root", "")),
        "target_database_path": str(manifest.get("target_database_path", "")),
        "target_identity": {"merge_run_id": merge_run_id},
    }
    confirmation_ref = _confirmation_receipt_ref(reconciliation_receipt)
    if confirmation_ref:
        payload["confirmation_receipt_ref"] = confirmation_ref
    return payload


def _selected_resolution_entries(reconciliation_receipt: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not reconciliation_receipt:
        return []
    entries = reconciliation_receipt.get("selected_resolutions", [])
    if not isinstance(entries, list):
        return []
    return [dict(item) for item in entries if isinstance(item, Mapping)]


def _confirmation_receipt_ref(reconciliation_receipt: Mapping[str, Any] | None) -> dict[str, Any]:
    if not reconciliation_receipt:
        return {}
    refs = reconciliation_receipt.get("confirmation_receipt_refs")
    if isinstance(refs, list):
        for item in refs:
            if isinstance(item, Mapping):
                return dict(item)
    if isinstance(refs, Mapping):
        return dict(refs)
    return {}
