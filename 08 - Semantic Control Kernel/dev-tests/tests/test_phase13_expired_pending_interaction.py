from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import ExpiredPendingInteraction, RecoveryContext, SemanticExceptionHandler
from semantic_control_kernel.domain.recovery.dialogs import RecoveryDialogService
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService


def _handler(paths: StatePaths) -> SemanticExceptionHandler:
    return SemanticExceptionHandler(
        recovery_event_store=RecoveryEventStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        support_bundle_service=SupportBundleService(SupportBundleStore(paths)),
    )


def test_target_same_expired_pending_interaction_reopens_dialog(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_expired",
            workflow_tool="manual_pipeline_run",
            failed_kernel_step="pending_input",
            target_identity={"target_hash": "same_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_expired"},
        ),
        lambda: (_ for _ in ()).throw(
            ExpiredPendingInteraction("interaction_expired", "The pending interaction expired.")
        ),
    )
    option = next(option for option in result.recovery_event.payload["recovery_options"] if option["agent_tool"] == "kernel_open_recovery_dialog")
    dialog = RecoveryDialogService().open_dialog(result.recovery_event.payload, option)

    assert dialog["kernel_dialog_state"]["target_identity"] == {"target_hash": "same_target"}
    assert "kernel_resume_state" in result.recovery_event.payload["allowed_agent_tools"]


def test_target_changed_expired_response_is_rejected_as_recovery_blocker(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_expired_changed",
            workflow_tool="manual_pipeline_run",
            failed_kernel_step="pending_input",
            target_identity={"target_hash": "changed_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_changed"},
        ),
        lambda: (_ for _ in ()).throw(
            ExpiredPendingInteraction("target_identity_changed", "The expired interaction target changed.")
        ),
    )

    assert result.recovery_event.payload["cause_code"] == "target_identity_changed"
    assert "kernel_open_recovery_dialog" in result.recovery_event.payload["allowed_agent_tools"]
    assert "accept expired" not in str(result.recovery_event.payload).lower()
