from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import MissingManifestOrOriginals, RecoveryContext, SemanticExceptionHandler
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


def test_missing_batch_manifest_and_originals_open_kernel_dialog_without_unsafe_deletion(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_missing",
            workflow_tool="manual_pipeline_run",
            failed_kernel_step="batch_manifest_reader",
            target_identity={"target_hash": "missing_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_missing"},
        ),
        lambda: (_ for _ in ()).throw(
            MissingManifestOrOriginals("batch_manifest_missing", "The cleanup batch manifest or originals are missing.")
        ),
    )
    event = result.recovery_event.payload
    dialog_option = next(option for option in event["recovery_options"] if option["agent_tool"] == "kernel_open_recovery_dialog")
    dialog = RecoveryDialogService().open_dialog(event, dialog_option)

    assert dialog["kernel_dialog_state"]["dialog_action"] == "missing_input_dialog or support dialog"
    assert "kernel_open_support_bundle" not in event["allowed_agent_tools"]
    assert all("delete" not in option["effect"] for option in event["recovery_options"])


def test_manual_filesystem_instruction_is_dialog_only_not_agent_payload(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_originals",
            workflow_tool="manual_pipeline_run",
            failed_kernel_step="originals_check",
            target_identity={"target_hash": "originals_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_originals"},
        ),
        lambda: (_ for _ in ()).throw(
            MissingManifestOrOriginals("originals_missing", "Original files are missing from the Artifact Tree.")
        ),
    )

    assert "user_filesystem_action" not in result.recovery_event.payload["allowed_agent_tools"]
    assert "kernel_open_recovery_dialog" in result.recovery_event.payload["allowed_agent_tools"]
    assert "kernel_cancel_active_run" in result.recovery_event.payload["allowed_agent_tools"]
