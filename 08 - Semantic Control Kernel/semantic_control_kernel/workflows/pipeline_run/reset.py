from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.batch_policy import reset_manifest_id
from semantic_control_kernel.policy.cleanup_policy import destructive_confirmation_matches
from semantic_control_kernel.repository.atomic_json import atomic_write_json
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.batches import PipelineRunExecution, PipelineRunTarget
from semantic_control_kernel.types.cleanup import DatabaseResetManifest
from semantic_control_kernel.workflows.pipeline_run.reset_final_notice import append_final_notice
from semantic_control_kernel.workflows.pipeline_run.reset_result_helpers import adapter_output, adapter_ref, block, manifest_ref, progress
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime


def reset_database(
    *,
    runtime: PipelineRunRuntime,
    target: PipelineRunTarget | None,
    confirmation: Mapping[str, Any] | None,
    workflow_run_id: str | None = None,
    batch_manifests: Sequence[Mapping[str, Any]] = (),
    reresolved_target_identity: Mapping[str, Any] | None = None,
) -> PipelineRunExecution:
    resolved_workflow_run_id = workflow_run_id or (target.workflow_run_id if target else "wr_missing_target")
    execution = PipelineRunExecution(
        workflow_run_id=resolved_workflow_run_id,
        workflow_tool="reset_database",
        state_root=Path(runtime.state_root),
        target=target,
    )
    if target is None:
        block(execution, "database_missing", "target_identity_changed", "Reset target is missing.")
        return execution
    ok, reason = destructive_confirmation_matches(
        confirmation,
        target_identity=target.target_identity,
        state_snapshot_id=target.state_snapshot_id,
        confirmation_scope="reset_database",
    )
    if not ok:
        block(execution, reason, "target_identity_changed" if reason == "target_identity_changed" else "expired_pending_interaction", "Reset requires a target-bound confirmation receipt.")
        return execution
    if reresolved_target_identity is not None and dict(reresolved_target_identity) != target.target_identity:
        block(execution, "target_identity_changed", "target_identity_changed", "Target identity changed after confirmation.")
        return execution
    progress(execution, "resetting_database", "running")
    result = runtime.corpus_adapter.reset_database(
        {
            "target_identity": target.target_identity,
            "database_path": target.database_path,
            "preserve_semantic_release": target.semantic_release_manifest_ref(),
            "confirmation": dict(confirmation or {}),
        }
    )
    if isinstance(result, MissingCapabilityBlocker):
        block(execution, "pipeline_capability_missing", "support_only_unrecoverable", result.to_dict().get("blocking_reason", "Required Pipeline capability is not available."))
        return execution
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        block(execution, "semantic_release_preservation_failed", "support_only_unrecoverable", f"CorpusAdapter.reset_database returned {result.status}.")
        return execution
    output = adapter_output(result)
    if output.get("semantic_release_preserved") is not True:
        block(execution, "semantic_release_preservation_failed", "support_only_unrecoverable", "Reset did not preserve semantic release identity.")
        return execution
    if output.get("empty_state_proven") is not True:
        block(execution, "semantic_release_preservation_failed", "support_only_unrecoverable", "Reset did not prove the post-reset database is empty.")
        return execution
    target_identity_after = output.get("target_identity_after", target.target_identity)
    if isinstance(target_identity_after, Mapping) and dict(target_identity_after) != target.target_identity:
        block(execution, "target_identity_changed", "target_identity_changed", "Reset owner returned a different target identity after mutation.")
        return execution
    reset_manifest = DatabaseResetManifest(
        workflow_run_id=resolved_workflow_run_id,
        reset_manifest_id=reset_manifest_id(resolved_workflow_run_id, target.database_path_hash),
        target_identity_before=target.target_identity,
        target_identity_after=dict(target_identity_after) if isinstance(target_identity_after, Mapping) else target.target_identity,
        preserved_release_ref=target.semantic_release_manifest_ref(),
        prior_semantic_release_state=target.semantic_release_state,
        post_reset_semantic_release_state=target.semantic_release_state,
        superseded_batch_refs=[manifest_ref(item) for item in batch_manifests],
        confirmation_receipt_ref=dict(confirmation or {}),
        reset_adapter_receipt_ref=adapter_ref(result),
        empty_state_proven=True,
    ).to_dict()
    path = Path(target.artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / "resets" / (reset_manifest["reset_manifest_id"] + ".json")
    atomic_write_json(path, reset_manifest)
    execution.artifacts["database_reset_manifest"] = reset_manifest
    execution.artifacts["database_reset_manifest_path"] = str(path)
    execution.artifacts["physical_compaction"] = dict(output.get("physical_compaction") or {})
    execution.artifacts["physical_compaction_performed"] = bool(output.get("physical_compaction_performed"))
    execution.status = "completed"
    execution.final_state = target.semantic_release_state
    execution.completed_step_ids.extend(("awaiting_confirmation", "resetting_database", "completed"))
    execution.operation_log.extend(("CorpusAdapter.reset_database", "kernel.database_reset_manifest.v1"))
    append_final_notice(execution, target=target, reset_manifest=reset_manifest, manifest_path=path, owner_output=output)
    progress(execution, "completed", "completed")
    return execution
