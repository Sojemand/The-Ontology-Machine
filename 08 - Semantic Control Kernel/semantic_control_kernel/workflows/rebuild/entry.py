from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semantic_control_kernel.policy.rebuild_policy import DEFAULT_EMBEDDING_POLICY
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker, RebuildWorkflowExecution
from semantic_control_kernel.workflows.rebuild.corpus_rebuild import run_corpus_builder
from semantic_control_kernel.workflows.rebuild.embeddings import create_embeddings
from semantic_control_kernel.workflows.rebuild.entry_activation import activate_loaded_release
from semantic_control_kernel.workflows.rebuild.entry_manifest import write_execution_manifest
from semantic_control_kernel.workflows.rebuild.entry_overwrite import confirm_overwrite_if_needed
from semantic_control_kernel.workflows.rebuild.entry_progress import (
    block_execution,
    complete_step,
    embedding_completion_summary,
    invalid_owner_response,
    release_locks,
    start_step,
)
from semantic_control_kernel.workflows.rebuild.entry_runtime import RebuildWorkflowRuntime
from semantic_control_kernel.workflows.rebuild.semantic_release_load import corpus_builder_load_semantic_release
from semantic_control_kernel.workflows.rebuild.target_path import resolve_target_database


def database_rebuild_from_artifacts(
    *,
    runtime: RebuildWorkflowRuntime,
    artifact_root: str | Path,
    target_database_name: str,
    workflow_run_id: str | None = None,
    rebuild_run_id: str | None = None,
    overwrite_receipt: Mapping[str, object] | None = None,
    embedding_policy: str = DEFAULT_EMBEDDING_POLICY,
    embedding_provider_configured: bool = False,
) -> RebuildWorkflowExecution:
    resolved_workflow_run_id = workflow_run_id or generate_id("workflow_run_id")
    resolved_rebuild_run_id = require_state_id("rebuild_run_id", rebuild_run_id or generate_id("rebuild_run_id"))
    try:
        target_path, target_identity = resolve_target_database(artifact_root=artifact_root, target_database_name=target_database_name)
    except ValueError as exc:
        return _invalid_target_execution(runtime, artifact_root, resolved_workflow_run_id, resolved_rebuild_run_id, str(exc))

    execution = _new_execution(runtime, artifact_root, target_path, resolved_workflow_run_id, resolved_rebuild_run_id)
    execution.artifacts["locks"] = [{"lock_id": f"lock_{resolved_rebuild_run_id}", "lock_type": "rebuild", "status": "active", "target_database_path": str(target_path)}]
    start_step(execution, "loading_semantic_release", "Loading Semantic Release from Artifact Tree.")
    loaded_release, load_result, blocker = corpus_builder_load_semantic_release(
        runtime.semantic_release_adapter,
        artifact_root=artifact_root,
        target_database_path=target_path,
    )
    if blocker is not None or loaded_release is None:
        block_execution(execution, blocker or invalid_owner_response("loading_semantic_release"))
        return execution
    execution.artifacts["loaded_release"] = dict(loaded_release)
    execution.artifacts["loaded_release_path"] = str(loaded_release["loaded_release_path"])
    complete_step(execution, "loading_semantic_release", "corpus_builder_load_semantic_release", adapter_results=[load_result])
    if target_path.exists() and not confirm_overwrite_if_needed(
        execution,
        artifact_root=artifact_root,
        target_path=target_path,
        target_identity=target_identity,
        loaded_release=loaded_release,
        overwrite_receipt=overwrite_receipt,
    ):
        return execution

    start_step(execution, "running_rebuild", "Rebuilding Corpus database from staged artifacts.")
    rebuild_output, rebuild_result, blocker = run_corpus_builder(
        runtime.corpus_adapter,
        artifact_root=artifact_root,
        target_database_path=target_path,
        loaded_release=loaded_release,
        workflow_run_id=resolved_workflow_run_id,
    )
    if blocker is not None or rebuild_output is None:
        block_execution(execution, blocker or invalid_owner_response("running_rebuild"))
        return execution
    complete_step(execution, "running_rebuild", "run_corpus_builder", adapter_results=[rebuild_result])

    start_step(execution, "creating_embeddings", "Creating embedding vectors for the rebuilt database. This can take a while.")
    embedding_result, embedding_adapter_result, blocker = create_embeddings(
        runtime.embedding_adapter,
        target_database_path=target_path,
        embedding_policy=embedding_policy,
        provider_configured=embedding_provider_configured,
    )
    if blocker is not None:
        execution.artifacts["rebuilt_database_visible"] = str(target_path)
        block_execution(execution, blocker)
        return execution
    complete_step(
        execution,
        "creating_embeddings",
        "create_embeddings",
        adapter_results=[embedding_adapter_result] if embedding_adapter_result is not None else [],
        summary=embedding_completion_summary(embedding_result, embedding_adapter_result),
    )
    activation_receipt = activate_loaded_release(runtime, execution, loaded_release)
    if activation_receipt is None:
        return execution
    write_execution_manifest(
        execution,
        artifact_root=artifact_root,
        target_path=target_path,
        loaded_release=loaded_release,
        rebuild_result=rebuild_result,
        embedding_policy=embedding_policy,
        embedding_result=embedding_result,
        embedding_adapter_result=embedding_adapter_result,
        activation_receipt=activation_receipt,
        record_count=int(rebuild_output.get("record_count", 0)),
        load_result=load_result,
    )
    release_locks(execution)
    complete_step(execution, "completed", "database_rebuild_from_artifacts", final_state="semantic_release_active")
    execution.status = "completed"
    from semantic_control_kernel.workflows.rebuild.final_notice import append_rebuild_final_notice

    append_rebuild_final_notice(execution)
    return execution


def _new_execution(
    runtime: RebuildWorkflowRuntime,
    artifact_root: str | Path,
    target_path: Path,
    workflow_run_id: str,
    rebuild_run_id: str,
) -> RebuildWorkflowExecution:
    return RebuildWorkflowExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="database_rebuild_from_artifacts",
        rebuild_run_id=rebuild_run_id,
        state_root=Path(runtime.state_root),
        artifact_root=str(Path(artifact_root).resolve(strict=False)),
        target_database_path=str(target_path),
    )


def _invalid_target_execution(
    runtime: RebuildWorkflowRuntime,
    artifact_root: str | Path,
    workflow_run_id: str,
    rebuild_run_id: str,
    summary: str,
) -> RebuildWorkflowExecution:
    execution = RebuildWorkflowExecution(
        workflow_run_id=workflow_run_id,
        workflow_tool="database_rebuild_from_artifacts",
        rebuild_run_id=rebuild_run_id,
        state_root=Path(runtime.state_root),
        artifact_root=str(Path(artifact_root).resolve(strict=False)),
        target_database_path="",
    )
    block_execution(
        execution,
        RebuildWorkflowBlocker(
            blocker_code="invalid_target_path",
            step_id="resolving_target_database",
            function_or_route="database_rebuild_from_artifacts",
            recovery_state_class="target_identity_changed",
            user_visible_summary=summary,
        ),
    )
    return execution


__all__ = ["RebuildWorkflowRuntime", "database_rebuild_from_artifacts"]
