from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evidence import first_evidence
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetIdentity, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver_support import blocker_payload
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.errors import BindingNotFoundError


def resolve_binding(
    binding_registry: DatabaseArtifactBindingRegistry | None,
    selector: TargetSelector,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    blocking: list[dict[str, Any]],
) -> dict[str, Any] | None:
    selector_payload = selector.to_dict()
    binding = None
    if binding_registry is not None:
        try:
            if selector_payload.get("database_id"):
                binding = binding_registry.get_by_database_id(selector_payload["database_id"]).to_dict()
            elif selector_payload.get("database_path"):
                binding = binding_registry.get_by_database_path(selector_payload["database_path"]).to_dict()
        except BindingNotFoundError:
            binding = None
    evidence_binding = first_evidence(bundle, kind="database_artifact_binding", source="kernel_store_binding")
    if evidence_binding is not None:
        binding = evidence_binding.payload_ref
    if binding is None and selector_payload.get("selected_existing_database"):
        blocking.append(blocker_payload("binding_missing", target_identity, "database binding", "missing", ()))
        return None
    if binding is not None:
        _validate_binding_against_owner_evidence(selector, target_identity, bundle, binding, blocking)
    return deepcopy(binding)


def _validate_binding_against_owner_evidence(
    selector: TargetSelector,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    binding: Mapping[str, Any],
    blocking: list[dict[str, Any]],
) -> None:
    selector_payload = selector.to_dict()
    if target_identity.database_path_hash and selector_payload.get("database_path") and not binding.get("database_path"):
        blocking.append(blocker_payload("binding_conflict", target_identity, "database binding", "database path missing", ()))
    owner_artifact = first_evidence(bundle, kind="artifact_tree_folder_contract", target_identity=target_identity)
    if owner_artifact is None or not owner_artifact.payload_ref.get("artifact_root_path"):
        return
    if binding.get("artifact_root_path") and owner_artifact.payload_ref["artifact_root_path"] != binding["artifact_root_path"]:
        blocking.append(
            blocker_payload(
                "owner_evidence_conflict",
                target_identity,
                "Kernel binding artifact root",
                "owner artifact root mismatch",
                (owner_artifact.evidence_ref_id,),
            )
        )


__all__ = ["resolve_binding"]
