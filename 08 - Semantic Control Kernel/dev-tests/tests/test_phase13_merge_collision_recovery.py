from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import MergeCollisionUnresolved, RecoveryContext, SemanticExceptionHandler
from semantic_control_kernel.domain.recovery.dialogs import RecoveryDialogService
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
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


def test_merge_collision_opens_reconciliation_dialog_and_cancel_archive_options(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_merge",
            workflow_tool="database_merge_additive_only",
            failed_kernel_step="reconcile_merged_database",
            target_identity={"target_hash": "merge_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_merge"},
            blocked_functions=("database_merge_additive_only",),
        ),
        lambda: (_ for _ in ()).throw(
            MergeCollisionUnresolved("merge_collision_unresolved", "Merge collision still needs a Kernel decision.")
        ),
    )
    event = result.recovery_event.payload
    dialog_option = next(option for option in event["recovery_options"] if option["agent_tool"] == "kernel_open_recovery_dialog")

    dialog = RecoveryDialogService().open_dialog(event, dialog_option)

    assert dialog["kernel_dialog_state"]["dialog_action"] == "merge_reconciliation_dialog"
    assert "kernel_cancel_active_run" in event["allowed_agent_tools"]
    assert "kernel_discard_or_archive_staged_work" in event["allowed_agent_tools"]


def test_stale_or_inconsistent_collision_manifest_never_silently_selects_policy(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_merge_stale",
            workflow_tool="filled_databases_merge_path",
            failed_kernel_step="collision_manifest",
            target_identity={"target_hash": "merge_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_merge"},
        ),
        lambda: (_ for _ in ()).throw(
            MergeCollisionUnresolved(
                "merge_collision_unresolved",
                "Collision manifest is stale.",
                technical_context={"stale_manifest": True, "support_bundle_required": True},
            )
        ),
    )
    event = result.recovery_event.payload
    option = next(option for option in event["recovery_options"] if option["agent_tool"] == "kernel_discard_or_archive_staged_work")
    archive = StagedWorkArchiveService(paths, RecoveryEventStore(paths)).archive_or_discard(
        event,
        option["recovery_id"],
        "failed_merge_target",
    )

    assert "policy" not in event["user_visible_cause"].lower()
    assert archive["result_status"] == "applied"
    assert event["support_bundle_ref"]["safe_summary"] == "Collision manifest is stale."
