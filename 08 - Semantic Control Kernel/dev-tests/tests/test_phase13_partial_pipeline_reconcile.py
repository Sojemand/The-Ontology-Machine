from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery.partial_pipeline_run import PartialPipelineRunReconciler
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION


def _event(paths: StatePaths):
    expires = RecoveryPolicy().expires_at(RecoveryStateClass.PARTIAL_PIPELINE_RUN.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_partial",
        recovery_state=RecoveryStateClass.PARTIAL_PIPELINE_RUN.value,
        target_identity={"target_hash": "partial_target"},
        state_snapshot_identity={"state_snapshot_id": "ss_partial"},
        expires_at=expires,
        safe_tools=("kernel_reconcile_partial_pipeline_run", "kernel_open_support_bundle"),
    )
    mirror = KernelMirrorEventService(MirrorEventStore(paths)).create_mirror_event(
        event_type=MirrorEventType.PIPELINE_ERROR.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Partial run.",
        current_state_summary="Partial recovery.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=("kernel_reconcile_partial_pipeline_run", "kernel_open_support_bundle"),
        tool_availability_expires_at=expires,
    )
    return RecoveryEventStore(paths).put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_reconcile_partial_pipeline_run", "kernel_open_support_bundle"],
            "blocked_functions": ["pipeline_run"],
            "cause_code": "partial_pipeline_run",
            "created_at": utc_iso(),
            "detected_by": "PartialPipelineRunReconciler",
            "expires_at": expires,
            "failed_kernel_step": "pipeline_run",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_partial",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": "partial_pipeline_run",
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": {"state_snapshot_id": "ss_partial"},
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": {"target_hash": "partial_target"},
            "user_visible_cause": "Pipeline run partially wrote output.",
            "workflow_run_id": "wr_partial",
            "workflow_tool": "manual_pipeline_run",
        }
    ), options[0]


def test_finalize_complete_enough_partial_run(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event, option = _event(paths)
    service = PartialPipelineRunReconciler(paths, RecoveryEventStore(paths))
    evidence = {
        "artifact_tree_output_refs_match": True,
        "complete_enough_to_finalize": True,
        "corpus_load_receipt_ref": "receipt",
        "database_record_counts_match": True,
        "manifest_ref": "manifest.json",
        "orchestrator_run_summary_ref": "run.json",
        "record_materialization_refs_match": True,
    }

    thin_finalize = service.reconcile(
        event.payload,
        option.payload["recovery_id"],
        "partial_ref",
        {
            key: value
            for key, value in evidence.items()
            if key != "database_record_counts_match"
        },
    )
    result = service.reconcile(event.payload, option.payload["recovery_id"], "partial_ref", evidence)

    assert thin_finalize["result_status"] == "support_only"
    assert result["result_status"] == "applied"
    assert result["finalized_manifest_ref"]["finalized_manifest_ref"] == "manifest.json"


def test_quarantine_when_partial_output_is_isolated_and_support_only_when_not(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event, option = _event(paths)
    service = PartialPipelineRunReconciler(paths, RecoveryEventStore(paths))

    quarantine = service.reconcile(
        event.payload,
        option.payload["recovery_id"],
        "partial_ref",
        {
            "affected_set_isolated": True,
            "isolation_evidence_source": "batch_manifest",
            "isolatable": True,
        },
    )
    weak_cleanup = service.reconcile(
        event.payload,
        option.payload["recovery_id"],
        "partial_ref",
        {"isolatable": True, "affected_set_isolated": True},
    )
    support = service.reconcile(event.payload, option.payload["recovery_id"], "partial_ref", {"isolatable": False})

    assert quarantine["quarantine_ref"]["quarantine_path"].startswith("quarantine/partial_writes/")
    assert quarantine["new_recovery_event_ref"]["quarantine_created"] is True
    assert quarantine["new_recovery_event_ref"]["quarantine_acknowledgement_required"] is True
    assert weak_cleanup["new_recovery_event_ref"]["quarantine_created"] is True
    assert support["result_status"] == "support_only"
