from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import RecoveryContext, SemanticExceptionHandler, TargetIdentityChanged
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.domain.recovery.tool_authorization import RecoveryToolAuthorization
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.agent_tool_surface_service import AgentToolSurfaceService
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION


TARGET = {"target_hash": "target_lifecycle"}
SNAPSHOT = {"state_snapshot_id": "ss_lifecycle"}


def _active_event(tmp_path: Path, tools=("kernel_open_recovery_dialog",)):
    paths = StatePaths.from_state_root(tmp_path / "state")
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_lifecycle",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        expires_at=expires_at,
        safe_tools=tools,
    )
    mirror = KernelMirrorEventService(mirror_store).create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Target changed.",
        current_state_summary="Recovery is active.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=tools,
        tool_availability_expires_at=expires_at,
    )
    event = recovery_store.put_recovery_event(
        {
            "allowed_agent_tools": list(tools),
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "target_identity_changed",
            "created_at": utc_iso(),
            "detected_by": "test",
            "expires_at": expires_at,
            "failed_kernel_step": "step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_lifecycle",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "Target changed.",
            "workflow_run_id": "wr_lifecycle",
            "workflow_tool": "manual_pipeline_run",
        }
    )
    return paths, recovery_store, mirror_store, event, options[0]


def test_recovery_tools_expose_only_through_matching_mirror_auto_call(tmp_path: Path) -> None:
    _paths, _recovery_store, mirror_store, event, option = _active_event(tmp_path)
    visible = AgentToolSurfaceService(mirror_store).list_event_scoped_tools(event.payload["mirror_event_id"])

    assert tuple(tool.tool_name for tool in visible) == ("kernel_open_recovery_dialog",)
    assert AgentToolSurfaceService(mirror_store).list_event_scoped_tools("missing") == ()
    assert option.payload["recovery_event_id"] == event.payload["recovery_event_id"]


def test_expiry_resolution_and_supersession_close_old_tool_calls(tmp_path: Path) -> None:
    _paths, recovery_store, mirror_store, event, option = _active_event(tmp_path)
    auth = RecoveryToolAuthorization(recovery_store, mirror_store)

    assert auth.authorize(
        tool_name="kernel_open_recovery_dialog",
        mirror_event_id=event.payload["mirror_event_id"],
        recovery_event_id=event.payload["recovery_event_id"],
        recovery_id=option.payload["recovery_id"],
    ).allowed

    mirror_store.mark_event_scoped_tools_expired(event.payload["mirror_event_id"], "event_resolved")
    assert not auth.authorize(
        tool_name="kernel_open_recovery_dialog",
        mirror_event_id=event.payload["mirror_event_id"],
        recovery_event_id=event.payload["recovery_event_id"],
        recovery_id=option.payload["recovery_id"],
    ).allowed

    recovery_store.update_status(event.payload["recovery_event_id"], "superseded", superseded_by=generate_id("recovery_event_id"))
    assert AgentToolSurfaceService(mirror_store).list_event_scoped_tools(event.payload["mirror_event_id"]) == ()


def test_new_recovery_event_supersedes_old_event_tools_without_manual_expiry(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    handler = SemanticExceptionHandler(
        recovery_event_store=recovery_store,
        mirror_event_service=KernelMirrorEventService(mirror_store),
        support_bundle_service=SupportBundleService(SupportBundleStore(paths)),
    )
    context = RecoveryContext(
        workflow_run_id="wr_supersede",
        workflow_tool="manual_pipeline_run",
        failed_kernel_step="target_step",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
    )
    first = handler.run_step(
        context,
        lambda: (_ for _ in ()).throw(TargetIdentityChanged("target_identity_changed", "Target changed.")),
    )
    first_event = first.recovery_event.payload
    first_option = next(option for option in first_event["recovery_options"] if option["agent_tool"] == "kernel_open_recovery_dialog")
    assert AgentToolSurfaceService(mirror_store).list_event_scoped_tools(first_event["mirror_event_id"])

    handler.run_step(
        context,
        lambda: (_ for _ in ()).throw(TargetIdentityChanged("target_identity_changed", "Target changed again.")),
    )

    superseded = recovery_store.get_recovery_event(first_event["recovery_event_id"]).payload
    assert superseded["status"] == "superseded"
    assert AgentToolSurfaceService(mirror_store).list_event_scoped_tools(first_event["mirror_event_id"]) == ()
    assert not RecoveryToolAuthorization(recovery_store, mirror_store).authorize(
        tool_name="kernel_open_recovery_dialog",
        mirror_event_id=first_event["mirror_event_id"],
        recovery_event_id=first_event["recovery_event_id"],
        recovery_id=first_option["recovery_id"],
    ).allowed
