from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.tool_authorization import validate_recovery_option_binding
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import RecoveryResultStatus


class PartialPipelineRunReconciler:
    def __init__(self, paths: StatePaths, recovery_store: RecoveryEventStore) -> None:
        self.paths = paths
        self.recovery_store = recovery_store
        self._json = AtomicJsonStore(paths, "partial_pipeline_run_recovery")

    def reconcile(self, recovery_event: Mapping[str, Any], recovery_id: str, partial_run_ref: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        _option, binding_error = validate_recovery_option_binding(
            self.recovery_store,
            recovery_event,
            recovery_id,
            "kernel_reconcile_partial_pipeline_run",
        )
        if binding_error is not None:
            return _rejected(
                self.recovery_store,
                recovery_event,
                recovery_id,
                partial_run_ref,
                binding_error,
                result_status="rejected",
            )
        if evidence.get("complete_enough_to_finalize") is True and _has_final_proof(evidence):
            finalized_ref = {"partial_run_ref": partial_run_ref, "finalized_manifest_ref": evidence.get("manifest_ref")}
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.APPLIED.value,
                selected_recovery_option={"outcome": "finalized_manifest"},
                written_refs=[finalized_ref],
            )
            return {
                "finalized_manifest_ref": finalized_ref,
                "new_recovery_event_ref": None,
                "quarantine_ref": None,
                "receipt": receipt,
                "result_status": "applied",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        if evidence.get("isolatable") is True:
            quarantine_id = generate_id("recovery_event_id").replace("rev_", "qrn_", 1)
            path = self.paths.quarantine_partial_writes_dir / f"{quarantine_id}.json"
            payload = {
                "created_at": utc_iso(),
                "partial_run_ref": partial_run_ref,
                "quarantine_id": quarantine_id,
                "schema_version": "repository.partial_pipeline_quarantine.v1",
                "source_evidence": dict(evidence),
            }
            self._json.write_json(path, payload)
            quarantine_ref = {"quarantine_id": quarantine_id, "quarantine_path": self.paths.relative_to_state_root(path)}
            receipt = self.recovery_store.append_recovery_receipt(
                recovery_event=recovery_event,
                recovery_id=recovery_id,
                result_status=RecoveryResultStatus.APPLIED.value,
                selected_recovery_option={"outcome": "quarantined"},
                written_refs=[quarantine_ref],
            )
            return {
                "finalized_manifest_ref": None,
                "new_recovery_event_ref": {
                    "quarantine_created": True,
                    "quarantine_acknowledgement_required": True,
                },
                "quarantine_ref": quarantine_ref,
                "receipt": receipt,
                "result_status": "applied",
                "support_bundle_ref": recovery_event.get("support_bundle_ref"),
            }
        return _rejected(
            self.recovery_store,
            recovery_event,
            recovery_id,
            partial_run_ref,
            "not_isolatable",
            result_status="support_only",
        )


def _has_final_proof(evidence: Mapping[str, Any]) -> bool:
    return all(
        evidence.get(key)
        for key in (
            "manifest_ref",
            "orchestrator_run_summary_ref",
            "corpus_load_receipt_ref",
            "database_record_counts_match",
            "record_materialization_refs_match",
            "artifact_tree_output_refs_match",
        )
    )


def _rejected(
    recovery_store: RecoveryEventStore,
    recovery_event: Mapping[str, Any],
    recovery_id: str,
    partial_run_ref: str,
    reason: str,
    *,
    result_status: str,
) -> dict[str, Any]:
    receipt = recovery_store.append_recovery_receipt(
        recovery_event=recovery_event,
        recovery_id=recovery_id,
        result_status=result_status,
        selected_recovery_option={"partial_run_ref": partial_run_ref, "outcome": reason},
        support_bundle_ref=recovery_event.get("support_bundle_ref"),
    )
    return {
        "finalized_manifest_ref": None,
        "new_recovery_event_ref": None,
        "quarantine_ref": None,
        "receipt": receipt,
        "result_status": result_status,
        "support_bundle_ref": recovery_event.get("support_bundle_ref"),
    }
