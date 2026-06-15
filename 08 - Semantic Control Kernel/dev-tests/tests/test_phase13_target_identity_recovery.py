from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import RecoveryContext, SemanticExceptionHandler, TargetIdentityChanged
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService


def _handler(paths: StatePaths):
    return SemanticExceptionHandler(
        recovery_event_store=RecoveryEventStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        support_bundle_service=SupportBundleService(SupportBundleStore(paths)),
    )


def test_target_identity_change_exposes_dialog_cancel_and_archive_options(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_target",
            workflow_tool="database_rebuild_from_artifacts",
            failed_kernel_step="confirmation_resume",
            target_identity={"target_hash": "new_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_target"},
            blocked_functions=("database_rebuild_from_artifacts",),
        ),
        lambda: (_ for _ in ()).throw(
            TargetIdentityChanged(
                cause_code="confirmation_stale",
                user_visible_cause="The target changed after confirmation.",
                blocked_functions=("database_rebuild_from_artifacts",),
            )
        ),
    )

    assert set(result.recovery_event.payload["allowed_agent_tools"]) == {
        "kernel_open_recovery_dialog",
        "kernel_resume_state",
        "kernel_cancel_active_run",
        "kernel_discard_or_archive_staged_work",
    }
    assert any(option["kernel_dialog_action"] for option in result.recovery_event.payload["recovery_options"])


def test_archive_discard_requires_confirmation_for_destructive_scope(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_target_archive",
            workflow_tool="manual_pipeline_run",
            failed_kernel_step="archive_step",
            target_identity={"target_hash": "target_archive"},
            state_snapshot_identity={"state_snapshot_id": "ss_archive"},
        ),
        lambda: (_ for _ in ()).throw(
            TargetIdentityChanged("target_identity_changed", "Target changed with staged work.")
        ),
    ).recovery_event.payload
    option = next(option for option in event["recovery_options"] if option["agent_tool"] == "kernel_discard_or_archive_staged_work")
    service = StagedWorkArchiveService(paths, RecoveryEventStore(paths))

    archived = service.archive_or_discard(event, option["recovery_id"], "staged_work_ref")
    rejected = service.archive_or_discard(
        event,
        option["recovery_id"],
        "staged_work_ref",
        destructive=True,
        confirmation_ref={"confirmation_receipt_id": "cfr_phase13"},
        scope_is_explicit=True,
    )

    assert archived["result_status"] == "applied"
    assert rejected["result_status"] == "rejected"
    assert rejected["archive_ref"] is None
