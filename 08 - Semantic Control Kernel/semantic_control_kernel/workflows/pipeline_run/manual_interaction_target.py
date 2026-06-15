from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.receipt_store import ReceiptStore
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunBlocker, PipelineRunTarget
from semantic_control_kernel.workflows.pipeline_run.manual_interaction_helpers import (
    adapter_output,
    clean_text,
    existing_corpus_databases,
    input_confirmation_identity,
    input_confirmation_request_id,
)
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime, adapter_failure_summary
from semantic_control_kernel.workflows.rebuild.target_path import resolve_target_database


def resolve_database_path(
    *,
    workflow_tool: str,
    workflow_run_id: str,
    artifact_root: str,
    target_database_name: str | None,
) -> tuple[Path | None, bool, PipelineRunBlocker | None]:
    corpus_dir = Path(artifact_root) / "Corpus"
    databases = existing_corpus_databases(corpus_dir)
    name = clean_text(target_database_name)
    if name is None:
        if len(databases) == 1:
            return databases[0], False, None
        if len(databases) > 1:
            return None, True, None
        return None, False, PipelineRunBlocker(
            blocker_code="database_missing",
            step_id="resolving_target_database",
            function_or_route=workflow_tool,
            recovery_state_class="target_identity_changed",
            user_visible_summary="No Corpus database was found in the selected Artifact Tree.",
            diagnostics=({"artifact_root": artifact_root, "workflow_run_id": workflow_run_id},),
        )
    try:
        target_path, _target_identity = resolve_target_database(
            artifact_root=artifact_root,
            target_database_name=name,
        )
    except ValueError as exc:
        return None, False, PipelineRunBlocker(
            blocker_code="invalid_target_path",
            step_id="resolving_target_database",
            function_or_route=workflow_tool,
            recovery_state_class="target_identity_changed",
            user_visible_summary=str(exc),
        )
    if not target_path.exists():
        return None, False, PipelineRunBlocker(
            blocker_code="database_missing",
            step_id="resolving_target_database",
            function_or_route=workflow_tool,
            recovery_state_class="target_identity_changed",
            user_visible_summary="The selected Corpus database does not exist.",
            diagnostics=({"target_database_path": str(target_path)},),
        )
    return target_path, False, None


def matching_input_confirmation_receipt(
    receipt_store: ReceiptStore,
    target: PipelineRunTarget,
    input_files: list[PipelineInputFile],
) -> dict[str, Any] | None:
    target_identity = input_confirmation_identity(target, input_files)
    expected_prefix = input_confirmation_request_id(target, input_files)
    for receipt in reversed(receipt_store.list_by_target(target_identity)):
        payload = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
        if payload.get("user_decision") != "confirmed":
            continue
        if not str(payload.get("confirmation_request_id") or "").startswith(expected_prefix):
            continue
        return dict(payload)
    return None


def read_active_release(
    runtime: PipelineRunRuntime,
    *,
    workflow_tool: str,
    target_database_path: Path,
) -> tuple[dict[str, Any], PipelineRunBlocker | None]:
    result = runtime.corpus_adapter.read_active_semantic_release(
        {"corpus_db_path": str(target_database_path)}
    )
    if isinstance(result, MissingCapabilityBlocker):
        payload = result.to_dict()
        return {}, PipelineRunBlocker(
            blocker_code="pipeline_capability_missing",
            step_id="loading_active_semantic_release",
            function_or_route=str(payload.get("kernel_function", workflow_tool)),
            recovery_state_class=str(payload.get("recovery_state_class", "support_only_unrecoverable")),
            user_visible_summary=str(payload.get("blocking_reason", "Required Pipeline capability is missing.")),
            diagnostics=tuple(dict(item) for item in payload.get("diagnostics", []) if isinstance(item, Mapping)),
        )
    if isinstance(result, AdapterCallResult) and result.status != "ok":
        return {}, PipelineRunBlocker(
            blocker_code=result.status,
            step_id="loading_active_semantic_release",
            function_or_route=workflow_tool,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary=f"{adapter_failure_summary(result).rstrip('.')} while loading the active Semantic Release.",
            diagnostics=tuple(dict(item) for item in result.to_dict().get("diagnostics", []) if isinstance(item, Mapping)),
        )
    output = adapter_output(result)
    if not output.get("release") and not output.get("release_id"):
        return {}, PipelineRunBlocker(
            blocker_code="semantic_release_missing",
            step_id="loading_active_semantic_release",
            function_or_route=workflow_tool,
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Manual pipeline run requires an active Semantic Release on the selected Corpus database.",
        )
    return output, None


__all__ = [
    "matching_input_confirmation_receipt",
    "read_active_release",
    "resolve_database_path",
]
