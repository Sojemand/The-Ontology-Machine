from __future__ import annotations

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.types.enums import AttachPointerOwner
from semantic_control_kernel.types.merge import MergeWorkflowExecution
from semantic_control_kernel.types.state import SemanticReleaseAttachState


def _write_attach_state(
    execution: MergeWorkflowExecution,
    *,
    release_path: str,
    release_id: str,
    release_version: str,
    release_fingerprint: str,
    runtime_locale: str,
    attach_receipt_id: str,
    target_database_path: str,
) -> None:
    paths = StatePaths.from_state_root(execution.state_root)
    paths.ensure_layout()
    AttachStateStore(paths).put_attach_state(
        SemanticReleaseAttachState(
            {
                "schema_version": SemanticReleaseAttachState.SCHEMA_VERSION,
                "release_path": release_path,
                "release_id": release_id,
                "release_version": release_version,
                "release_fingerprint": release_fingerprint,
                "runtime_locale": runtime_locale,
                "target_database_path": target_database_path,
                "attach_receipt_id": attach_receipt_id,
                "attached_at": utc_iso(),
                "pointer_owner": AttachPointerOwner.KERNEL_HELD.value,
            }
        )
    )
