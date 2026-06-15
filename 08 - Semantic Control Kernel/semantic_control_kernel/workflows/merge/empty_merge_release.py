from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.runtime_locale import control_locale_or_default
from semantic_control_kernel.types.merge import MergeWorkflowBlocker, MergeWorkflowExecution
from semantic_control_kernel.workflows.merge.empty_merge_attach_state import _write_attach_state
from semantic_control_kernel.workflows.merge.empty_merge_release_refs import (
    _release_path_from_write_output,
    _release_ref_from_create_output,
    _release_ref_from_write_output,
)
from semantic_control_kernel.workflows.merge.empty_merge_support import _fail_locks, _target_identity
from semantic_control_kernel.workflows.merge.receipts import adapter_output, block_execution, blocker_from_adapter_result, complete_step, start_step


def _finalize_release(
    runtime: object,
    execution: MergeWorkflowExecution,
    selection: Mapping[str, Any],
    semantic_package: Mapping[str, Any],
    *,
    id_map: Mapping[str, Any] | None,
) -> bool:
    taxonomy_ref = dict(semantic_package.get("taxonomy_ref", {})) if isinstance(semantic_package.get("taxonomy_ref"), Mapping) else {}
    projection_refs = [dict(item) for item in semantic_package.get("projection_refs", []) if isinstance(item, Mapping)] if isinstance(semantic_package.get("projection_refs"), list) else []
    if not taxonomy_ref or not projection_refs:
        return _block_incomplete_release(execution, "Merged semantic package is missing reconciled taxonomy/projection refs.")
    semantic_release_root = Path(str(semantic_package.get("target_semantic_release_folder") or Path(selection["target_artifact_root"]) / "Semantic Release"))
    payload = _release_payload(execution, selection, semantic_package, taxonomy_ref, projection_refs, semantic_release_root, id_map)
    start_step(
        execution,
        "attaching_semantic_release",
        "Creating and writing the merged Semantic Release before it is attached to the target database.",
    )
    create_result = runtime.semantic_release_adapter.create_custom_semantic_release(payload)
    blocker = blocker_from_adapter_result("attaching_semantic_release", create_result, function_name="create_custom_semantic_release")
    if blocker is not None:
        return _block_release(execution, blocker)
    release_ref = _release_ref_from_create_output(adapter_output(create_result))
    release_path = str(semantic_release_root / "releases" / str(release_ref.get("release_id", "")).strip() / "release.json")
    if not _release_identity_complete(release_ref):
        return _block_incomplete_release(execution, "Custom merged Semantic Release was created without a complete identity proof.")
    execution.artifacts["custom_release_path"] = release_path
    execution.artifacts["custom_release_ref"] = dict(release_ref)
    write_result = runtime.semantic_release_adapter.write_semantic_release(
        {**payload, "release_path": release_path, "release_ref": release_ref, "semantic_release_path": str(semantic_release_root)}
    )
    blocker = blocker_from_adapter_result("attaching_semantic_release", write_result, function_name="write_semantic_release")
    if blocker is not None:
        return _block_release(execution, blocker)
    release_ref = _release_ref_from_write_output(adapter_output(write_result), fallback=release_ref)
    release_path = _release_path_from_write_output(adapter_output(write_result), fallback=release_path)
    if not _release_identity_complete(release_ref):
        return _block_incomplete_release(execution, "Custom merged Semantic Release was written without a complete identity proof.")
    execution.artifacts["custom_release_path"] = release_path
    execution.artifacts["custom_release_ref"] = dict(release_ref)
    receipt = complete_step(
        execution,
        step_id="attaching_semantic_release",
        function_name="attach_custom_semantic_release_to_database",
        adapter_results=[create_result, write_result],
        output_refs=[{**dict(release_ref), "release_path": release_path}],
        final_state="semantic_release_complete_not_active",
    )
    _write_attach_state(
        execution,
        release_path=release_path,
        release_id=str(release_ref["release_id"]),
        release_version=str(release_ref["release_version"]),
        release_fingerprint=str(release_ref["release_fingerprint"]),
        runtime_locale=str(payload["runtime_locale"]),
        attach_receipt_id=_receipt_id(receipt),
        target_database_path=str(selection["target_database_path"]),
    )
    return _activate_release(runtime, execution, selection, payload, release_path, release_ref)


def _release_payload(
    execution: MergeWorkflowExecution,
    selection: Mapping[str, Any],
    semantic_package: Mapping[str, Any],
    taxonomy_ref: Mapping[str, Any],
    projection_refs: list[Mapping[str, Any]],
    semantic_release_root: Path,
    id_map: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "collision_manifest": dict(execution.artifacts.get("collision_manifest", {})),
        "id_map": dict(id_map or {}),
        "merge_context": {"collision_manifest": dict(execution.artifacts.get("collision_manifest", {})), "id_map": dict(id_map or {}), "merge_run_id": execution.merge_run_id},
        "merge_run_id": execution.merge_run_id,
        "projection_refs": projection_refs,
        "release_identity_policy": dict(semantic_package.get("release_identity_policy", {})) if isinstance(semantic_package.get("release_identity_policy"), Mapping) else {},
        "runtime_locale": control_locale_or_default(semantic_package.get("runtime_locale"), taxonomy_ref.get("runtime_locale")),
        "semantic_merge_package": dict(semantic_package),
        "semantic_release_folder": str(semantic_release_root),
        "target_database_path": selection["target_database_path"],
        "target_semantic_release_folder": str(semantic_release_root),
        "target_identity": _target_identity(selection),
        "taxonomy_ref": dict(taxonomy_ref),
    }


def _activate_release(
    runtime: object,
    execution: MergeWorkflowExecution,
    selection: Mapping[str, Any],
    payload: Mapping[str, Any],
    release_path: str,
    release_ref: Mapping[str, Any],
) -> bool:
    activation_payload = {**dict(payload), "corpus_db_path": selection["target_database_path"], "release_path": release_path, "release_ref": release_ref}
    start_step(
        execution,
        "activating_semantic_release",
        "Preflighting and activating the merged Semantic Release for the target corpus database.",
    )
    preflight = runtime.semantic_release_adapter.preflight_semantic_release_activation(activation_payload)
    blocker = blocker_from_adapter_result("activating_semantic_release", preflight, function_name="activate_semantic_release")
    if blocker is not None:
        return _block_release(execution, blocker)
    activation = runtime.semantic_release_adapter.activate_semantic_release(activation_payload)
    blocker = blocker_from_adapter_result("activating_semantic_release", activation, function_name="activate_semantic_release")
    if blocker is not None:
        return _block_release(execution, blocker)
    complete_step(
        execution,
        step_id="activating_semantic_release",
        function_name="activate_semantic_release",
        adapter_results=[preflight, activation],
        final_state="semantic_release_active",
    )
    return True


def _release_identity_complete(release_ref: Mapping[str, Any]) -> bool:
    return all(str(release_ref.get(key, "")).strip() for key in ("release_id", "release_version", "release_fingerprint"))


def _block_release(execution: MergeWorkflowExecution, blocker: MergeWorkflowBlocker) -> bool:
    _fail_locks(execution)
    block_execution(execution, blocker)
    return False


def _block_incomplete_release(execution: MergeWorkflowExecution, summary: str) -> bool:
    return _block_release(execution, _release_incomplete(summary))


def _release_incomplete(summary: str) -> MergeWorkflowBlocker:
    return MergeWorkflowBlocker("release_incomplete", "attaching_semantic_release", "create_custom_semantic_release", "semantic_release_incomplete_staged", summary)


def _receipt_id(receipt: object) -> str:
    if hasattr(receipt, "to_dict"):
        return str(receipt.to_dict().get("operation_receipt_id", ""))
    return ""
