from __future__ import annotations

from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution


def invalid_owner_response(step_id: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker(
        "invalid_owner_response",
        step_id,
        step_id,
        "support_only_unrecoverable",
        "Merge owner returned an invalid response.",
    )


def id_map_invalid(detail: str) -> MergeWorkflowBlocker:
    provenance_fields = (
        "semantic_release_id",
        "semantic_release_version",
        "release_fingerprint",
        "taxonomy_fingerprint",
        "projection_id",
        "projection_fingerprint",
    )
    if any(field in detail for field in provenance_fields):
        return MergeWorkflowBlocker(
            "materialization_provenance_missing",
            "merge_database_filled_additive",
            "merge_database_filled_additive",
            "support_only_unrecoverable",
            "Filled merge cannot preserve record materialization provenance.",
            diagnostics=({"reason": detail},),
        )
    return MergeWorkflowBlocker(
        "invalid_owner_response",
        "running_filled_merge",
        "merge_database_filled_additive",
        "support_only_unrecoverable",
        "Filled merge returned an incomplete ID map.",
        diagnostics=({"reason": detail},),
    )


def mark_locks_failed(execution: MergeWorkflowExecution) -> None:
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "failed"


def release_locks(execution: MergeWorkflowExecution) -> None:
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "released"
