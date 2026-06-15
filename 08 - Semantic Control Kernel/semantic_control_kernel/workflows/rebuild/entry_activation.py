from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.types.enums import AttachPointerOwner
from semantic_control_kernel.types.rebuild import RebuildWorkflowExecution
from semantic_control_kernel.types.state import SemanticReleaseAttachState
from semantic_control_kernel.workflows.rebuild.entry_progress import (
    block_execution,
    blocker_from_result,
    complete_step,
    start_step,
)
from semantic_control_kernel.workflows.rebuild.entry_runtime import RebuildWorkflowRuntime


def activate_loaded_release(
    runtime: RebuildWorkflowRuntime,
    execution: RebuildWorkflowExecution,
    loaded_release: Mapping[str, Any],
) -> str | None:
    payload = {
        "corpus_db_path": execution.target_database_path,
        "loaded_semantic_release": dict(loaded_release),
        "release_ref": {
            "release_fingerprint": loaded_release["loaded_release_fingerprint"],
            "release_id": loaded_release["loaded_semantic_release_id"],
            "release_version": loaded_release["loaded_semantic_release_version"],
        },
        "release_path": loaded_release["loaded_release_path"],
        "target_identity": execution.target_identity,
    }
    start_step(execution, "attaching_semantic_release", "Attaching loaded Semantic Release to rebuilt database.")
    load_result = runtime.semantic_release_adapter.load_semantic_release(payload)
    blocker = blocker_from_result("attaching_semantic_release", load_result, "attach_custom_semantic_release_to_database")
    if blocker is not None:
        block_execution(execution, blocker)
        return None
    start_step(execution, "activating_semantic_release", "Activating Semantic Release on rebuilt database.")
    preflight = runtime.semantic_release_adapter.preflight_semantic_release_activation(payload)
    blocker = blocker_from_result("activating_semantic_release", preflight, "activate_semantic_release")
    if blocker is not None:
        block_execution(execution, blocker)
        return None
    activate = runtime.semantic_release_adapter.activate_semantic_release(payload)
    blocker = blocker_from_result("activating_semantic_release", activate, "activate_semantic_release")
    if blocker is not None:
        block_execution(execution, blocker)
        return None
    attach_receipt_id = complete_step(
        execution,
        "attaching_semantic_release",
        "attach_custom_semantic_release_to_database",
        adapter_results=[load_result, preflight],
        final_state="semantic_release_complete_not_active",
    )
    write_attach_state(
        execution,
        release_path=str(loaded_release["loaded_release_path"]),
        release_id=str(loaded_release["loaded_semantic_release_id"]),
        release_version=str(loaded_release["loaded_semantic_release_version"]),
        release_fingerprint=str(loaded_release["loaded_release_fingerprint"]),
        runtime_locale=control_locale_or_default(loaded_release.get("runtime_locale")),
        attach_receipt_id=attach_receipt_id,
    )
    return complete_step(
        execution,
        "activating_semantic_release",
        "activate_semantic_release",
        adapter_results=[preflight, activate],
        final_state="semantic_release_active",
    )


def write_attach_state(
    execution: RebuildWorkflowExecution,
    *,
    release_path: str,
    release_id: str,
    release_version: str,
    release_fingerprint: str,
    runtime_locale: str,
    attach_receipt_id: str,
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
                "runtime_locale": control_locale_or_default(runtime_locale),
                "target_database_path": execution.target_database_path,
                "attach_receipt_id": attach_receipt_id,
                "attached_at": utc_iso(),
                "pointer_owner": AttachPointerOwner.KERNEL_HELD.value,
            }
        )
    )


__all__ = ["activate_loaded_release"]
