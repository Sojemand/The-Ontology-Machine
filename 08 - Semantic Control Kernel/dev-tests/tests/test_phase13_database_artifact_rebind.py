from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery.rebind_database_artifact_tree import DatabaseArtifactRebindService
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION


TARGET = {"target_hash": "binding_target"}
SNAPSHOT = {"state_snapshot_id": "ss_binding"}


def _event(paths: StatePaths):
    expires = RecoveryPolicy().expires_at(RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_binding",
        recovery_state=RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value,
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        expires_at=expires,
        safe_tools=("kernel_rebind_database_artifact_tree", "kernel_open_recovery_dialog", "kernel_open_support_bundle"),
    )
    mirror = KernelMirrorEventService(MirrorEventStore(paths)).create_mirror_event(
        event_type=MirrorEventType.PIPELINE_ERROR.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Binding broken.",
        current_state_summary="Binding recovery.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=("kernel_rebind_database_artifact_tree", "kernel_open_recovery_dialog", "kernel_open_support_bundle"),
        tool_availability_expires_at=expires,
    )
    return RecoveryEventStore(paths).put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_rebind_database_artifact_tree", "kernel_open_recovery_dialog", "kernel_open_support_bundle"],
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "binding_missing",
            "created_at": utc_iso(),
            "detected_by": "DatabaseArtifactBindingRegistry",
            "expires_at": expires,
            "failed_kernel_step": "binding_step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_binding",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": "broken_database_artifact_binding",
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "Binding missing.",
            "workflow_run_id": "wr_binding",
            "workflow_tool": "manual_pipeline_run",
        }
    ), options[0]


def test_provable_metadata_rebinds_and_writes_receipt(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event, option = _event(paths)

    result = DatabaseArtifactRebindService(RecoveryEventStore(paths)).rebind(
        event.payload,
        option.payload["recovery_id"],
        "binding_recovery_001",
        {
            "artifact_tree_id": "artifact_001",
            "artifact_tree_contract_valid": True,
            "binding_metadata_matches": True,
            "database_id": "database_001",
            "database_path_exists": True,
            "is_corpus_database": True,
            "proof_status": "provable",
            "target_identity": TARGET,
        },
    )

    assert result["result_status"] == "applied"
    assert result["database_artifact_binding_ref"]["database_id"] == "database_001"
    assert result["receipt"].payload["written_refs"]


def test_user_selection_dialog_path_and_support_only_never_guess_nearest_folder(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event, option = _event(paths)
    service = DatabaseArtifactRebindService(RecoveryEventStore(paths))

    thin_proof = service.rebind(
        event.payload,
        option.payload["recovery_id"],
        "binding_recovery_thin",
        {
            "artifact_tree_contract_valid": True,
            "database_path_exists": True,
            "is_corpus_database": True,
            "proof_status": "provable",
            "target_identity": TARGET,
        },
    )
    dialog = service.rebind(
        event.payload,
        option.payload["recovery_id"],
        "binding_recovery_002",
        {
            "artifact_tree_contract_valid": True,
            "database_path_exists": True,
            "is_corpus_database": True,
            "proof_status": "needs_user_selection",
        },
    )
    support = service.rebind(event.payload, option.payload["recovery_id"], "binding_recovery_003", {"proof_status": "nearest_path_only"})

    assert thin_proof["result_status"] == "support_only"
    assert dialog["result_status"] == "dialog_required"
    assert support["result_status"] == "support_only"
    assert support["database_artifact_binding_ref"] is None
