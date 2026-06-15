from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semantic_control_kernel.types.rebuild import RebuildWorkflowExecution
from semantic_control_kernel.workflows.rebuild.entry_progress import block_execution
from semantic_control_kernel.workflows.rebuild.target_path import overwrite_blocker


def confirm_overwrite_if_needed(
    execution: RebuildWorkflowExecution,
    *,
    artifact_root: str | Path,
    target_path: Path,
    target_identity: Mapping[str, object],
    loaded_release: Mapping[str, object],
    overwrite_receipt: Mapping[str, object] | None,
) -> bool:
    blocker = overwrite_blocker(
        overwrite_receipt,
        artifact_root=artifact_root,
        target_database_path=target_path,
        loaded_release_fingerprint=loaded_release["loaded_release_fingerprint"],
        workflow_run_id=execution.workflow_run_id,
    )
    if blocker is not None:
        execution.artifacts["overwrite_required_for"] = {
            **target_identity,
            "loaded_release_fingerprint": loaded_release["loaded_release_fingerprint"],
            "workflow_run_id": execution.workflow_run_id,
        }
        block_execution(execution, blocker)
        return False
    execution.artifacts["overwrite_receipt_id"] = str(overwrite_receipt.get("confirmation_receipt_id", "overwrite_receipt"))
    execution.artifacts["locks"].append(
        {
            "lock_id": f"lock_overwrite_{execution.rebuild_run_id}",
            "lock_type": "destructive_target_database",
            "status": "active",
            "target_database_path": str(target_path),
        }
    )
    return True


__all__ = ["confirm_overwrite_if_needed"]
