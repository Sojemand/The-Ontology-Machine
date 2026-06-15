from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution
from semantic_control_kernel.workflows.merge.receipts import merge_run_dir, write_json


def _write_selection(execution: MergeWorkflowExecution) -> None:
    if not execution.selection:
        return
    path = merge_run_dir(execution.selection["target_artifact_root"], execution.merge_run_id) / "merge_selection.json"
    execution.artifacts["merge_selection_path"] = write_json(path, execution.selection)


def _require_route(selection: Mapping[str, Any], state: str) -> MergeWorkflowBlocker | None:
    sources = [source for source in selection.get("source_databases", []) if isinstance(source, Mapping)]
    source_states = {str(source.get("source_state") or "") for source in sources}
    if state == "filled" and source_states <= {"empty", "filled"} and "filled" in source_states:
        return None
    bad = [source for source in sources if source.get("source_state") != state]
    if not bad:
        return None
    blocker_code = "source_state_unknown" if any(str(source.get("source_state") or "") not in {"empty", "filled"} for source in bad) else "merge_mixed_emptiness"
    return MergeWorkflowBlocker(
        blocker_code=blocker_code,
        step_id="classifying_merge_route",
        function_or_route="empty_databases_merge_path" if state == "empty" else "filled_databases_merge_path",
        recovery_state_class="none",
        user_visible_summary="Selected source databases no longer match the classified merge route.",
    )


def _target_identity(selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "merge_run_id": selection["merge_run_id"],
        "target_artifact_root": selection["target_artifact_root"],
        "target_database_path": selection["target_database_path"],
    }


def _invalid(step_id: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker("invalid_owner_response", step_id, step_id, "support_only_unrecoverable", "Merge owner returned an invalid response.")


def _unresolved(step_id: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker("merge_collision_unresolved", step_id, step_id, "unresolved_merge_collision", "Merge collision manifest still blocks activation.")


def _fail_locks(execution: MergeWorkflowExecution) -> None:
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "failed"


def _release_locks(execution: MergeWorkflowExecution) -> None:
    for lock in execution.artifacts.get("locks", []):
        if lock.get("status") == "active":
            lock["status"] = "released"
