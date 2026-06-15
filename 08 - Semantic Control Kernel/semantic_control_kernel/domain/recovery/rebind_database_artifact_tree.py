from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.tool_authorization import validate_recovery_option_binding
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import RecoveryResultStatus


class DatabaseArtifactRebindService:
    def __init__(self, recovery_store: RecoveryEventStore) -> None:
        self.recovery_store = recovery_store

    def rebind(
        self,
        recovery_event: Mapping[str, Any],
        recovery_id: str,
        binding_recovery_id: str,
        proof: Mapping[str, Any],
    ) -> dict[str, Any]:
        _option, binding_error = validate_recovery_option_binding(
            self.recovery_store,
            recovery_event,
            recovery_id,
            "kernel_rebind_database_artifact_tree",
        )
        if binding_error is not None:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                binding_recovery_id,
                binding_error,
                result_status="rejected",
            )

        if _has_provable_binding(recovery_event, proof):
            binding_receipt_id = generate_id("operation_receipt_id")
            binding_ref = {
                "binding_recovery_id": binding_recovery_id,
                "binding_receipt_id": binding_receipt_id,
                "database_id": proof.get("database_id"),
                "artifact_tree_id": proof.get("artifact_tree_id"),
            }
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.APPLIED.value,
                selected_recovery_option={"binding_recovery_id": binding_recovery_id},
                written_refs=[binding_ref],
            )
            return {
                "binding_receipt_id": binding_receipt_id,
                "database_artifact_binding_ref": binding_ref,
                "receipt": receipt,
                "result_status": "applied",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        if _needs_user_selection(proof):
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.REJECTED.value,
                selected_recovery_option={
                    "binding_recovery_id": binding_recovery_id,
                    "dialog": "rebind_database_artifact_tree_dialog",
                    "rejection_reason": "binding_proof_requires_user_selection",
                },
            )
            return {
                "binding_receipt_id": None,
                "database_artifact_binding_ref": None,
                "receipt": receipt,
                "result_status": "dialog_required",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        return _rejected(
            self.recovery_store,
            recovery_event,
            recovery_id,
            binding_recovery_id,
            "insufficient_binding_proof",
            result_status="support_only",
        )


def _has_provable_binding(recovery_event: Mapping[str, Any], proof: Mapping[str, Any]) -> bool:
    if proof.get("proof_status") != "provable":
        return False
    if proof.get("target_identity") != recovery_event.get("target_identity"):
        return False
    if not isinstance(proof.get("database_id"), str) or not proof.get("database_id"):
        return False
    if not isinstance(proof.get("artifact_tree_id"), str) or not proof.get("artifact_tree_id"):
        return False
    if proof.get("database_path_exists") is not True:
        return False
    if proof.get("is_corpus_database") is not True:
        return False
    if proof.get("artifact_tree_contract_valid") is not True:
        return False
    return any(
        proof.get(key) is True
        for key in (
            "binding_metadata_matches",
            "active_release_pointer_matches",
            "batch_manifest_matches",
            "stored_binding_evidence_matches",
        )
    )


def _needs_user_selection(proof: Mapping[str, Any]) -> bool:
    return (
        proof.get("proof_status") == "needs_user_selection"
        and proof.get("database_path_exists") is True
        and proof.get("is_corpus_database") is True
        and proof.get("artifact_tree_contract_valid") is True
    )


def _rejected(
    recovery_store: RecoveryEventStore,
    recovery_event: Mapping[str, Any],
    recovery_id: str,
    binding_recovery_id: str,
    reason: str,
    *,
    result_status: str,
) -> dict[str, Any]:
    receipt = recovery_store.append_recovery_receipt(
        recovery_event=recovery_event,
        recovery_id=recovery_id,
        result_status=result_status,
        selected_recovery_option={"binding_recovery_id": binding_recovery_id, "reason": reason},
        support_bundle_ref=recovery_event.get("support_bundle_ref"),
    )
    return {
        "binding_receipt_id": None,
        "database_artifact_binding_ref": None,
        "receipt": receipt,
        "result_status": result_status,
        "support_bundle_ref": recovery_event.get("support_bundle_ref"),
    }
