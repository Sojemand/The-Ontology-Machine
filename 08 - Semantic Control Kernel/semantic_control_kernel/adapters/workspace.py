from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter
from semantic_control_kernel.types.adapter_results import MissingCapabilityBlocker


class WorkspaceAdapter(BasePipelineAdapter):
    adapter_name = "WorkspaceAdapter"

    def prepare_artifact_tree(
        self,
        request_payload: Mapping[str, Any] | None = None,
        *,
        kernel_function: str = "create_standard_artifact_folder_tree",
    ) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        owner_request = _artifact_tree_create_request(self, payload)
        if owner_request is None:
            return self.blocked_by_kernel_precondition(
                kernel_function=kernel_function,
                capability_status="implemented_in_pipeline",
                summary="Artifact Tree creation requires a resolved artifact root path.",
                missing_fields=("artifact_root_path",),
            )
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="00 - Orchestrator",
            owner_contract_module="orchestrator.orchestrator_contract",
            owner_action="create_artifact_tree",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("artifact_root_path_hash",),
            target_identity=owner_request.get("target_identity") if isinstance(owner_request.get("target_identity"), Mapping) else None,
        )

    def validate_artifact_tree(
        self,
        request_payload: Mapping[str, Any] | None = None,
        *,
        kernel_function: str = "store_active_artifact_folder_tree",
    ) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        owner_request = _artifact_tree_validate_request(self, payload)
        if owner_request is None:
            return self.blocked_by_kernel_precondition(
                kernel_function=kernel_function,
                capability_status="implemented_in_pipeline",
                summary="Artifact Tree validation requires a resolved artifact root path.",
                missing_fields=("artifact_root_path",),
            )
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="00 - Orchestrator",
            owner_contract_module="orchestrator.orchestrator_contract",
            owner_action="validate_artifact_tree",
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
            target_identity=owner_request.get("target_identity") if isinstance(owner_request.get("target_identity"), Mapping) else None,
        )


from pathlib import Path

from semantic_control_kernel.adapters.base import READ_ONLY_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


def _artifact_tree_create_request(adapter: WorkspaceAdapter, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    target = payload.get("target") if isinstance(payload.get("target"), Mapping) else None
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else None
    artifact_root = (
        str(payload.get("artifact_root_path") or "")
        or (str(target.get("artifact_root_path", "")) if isinstance(target, Mapping) else "")
        or (str(selection.get("target_artifact_root", "")) if isinstance(selection, Mapping) else "")
    )
    if not artifact_root:
        return None
    artifact_path = Path(artifact_root)
    target_identity = adapter.target_identity(payload, artifact_root_path=artifact_path)
    # The Orchestrator validates the owner-facing artifact-root hash format
    # directly, so normalize this field to the owner's full sha256 path hash.
    target_identity["artifact_root_path_hash"] = adapter.owner_path_hash(artifact_path)
    return adapter.phase19_request(
        owner_action="create_artifact_tree",
        request_payload=payload,
        target_identity=target_identity,
        artifact_root_parent=str(artifact_path.parent),
        artifact_root_name=artifact_path.name,
        create_mode=str(payload.get("create_mode") or "idempotent_create"),
        folder_contract_version="kernel_artifact_tree.v1",
    )


def _artifact_tree_validate_request(adapter: WorkspaceAdapter, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    target = payload.get("target") if isinstance(payload.get("target"), Mapping) else None
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else None
    artifact_root = (
        str(payload.get("artifact_root_path") or "")
        or (str(target.get("artifact_root_path", "")) if isinstance(target, Mapping) else "")
        or (str(selection.get("target_artifact_root", "")) if isinstance(selection, Mapping) else "")
    )
    if not artifact_root:
        return None
    target_identity = adapter.target_identity(payload, artifact_root_path=artifact_root)
    target_identity["artifact_root_path_hash"] = adapter.owner_path_hash(artifact_root)
    return adapter.phase19_request(
        owner_action="validate_artifact_tree",
        request_payload=payload,
        target_identity=target_identity,
        artifact_root_path=artifact_root,
        folder_contract_version="kernel_artifact_tree.v1",
        return_unexpected_paths=True,
    )
