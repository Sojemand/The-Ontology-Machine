from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semantic_control_kernel.types.rebuild import RebuildWorkflowExecution
from semantic_control_kernel.workflows.rebuild.entry_progress import adapter_call_id
from semantic_control_kernel.workflows.rebuild.manifest import build_rebuild_manifest, write_rebuild_manifest


def write_execution_manifest(
    execution: RebuildWorkflowExecution,
    *,
    artifact_root: str | Path,
    target_path: Path,
    loaded_release: Mapping[str, object],
    rebuild_result: object,
    embedding_policy: str,
    embedding_result: str,
    embedding_adapter_result: object | None,
    activation_receipt: str,
    record_count: int,
    load_result: object,
) -> None:
    manifest = build_rebuild_manifest(
        rebuild_run_id=execution.rebuild_run_id,
        workflow_run_id=execution.workflow_run_id,
        artifact_root=str(Path(artifact_root).resolve(strict=False)),
        target_database_path=str(target_path),
        loaded_release=loaded_release,
        corpus_builder_run_ref={"adapter_call_id": adapter_call_id(rebuild_result), "database_path": str(target_path)},
        embedding_policy=embedding_policy,
        embedding_result=embedding_result,
        activation_receipt_id=activation_receipt,
        record_count=record_count,
        overwrite_receipt_id=execution.artifacts.get("overwrite_receipt_id"),
        adapter_call_refs=[
            {"adapter_call_id": adapter_call_id(item)}
            for item in (load_result, rebuild_result, embedding_adapter_result)
            if item is not None
        ],
    ).to_dict()
    path = write_rebuild_manifest(artifact_root, execution.rebuild_run_id, manifest)
    execution.artifacts["rebuild_manifest"] = manifest
    execution.artifacts["rebuild_manifest_path"] = path


__all__ = ["write_execution_manifest"]
