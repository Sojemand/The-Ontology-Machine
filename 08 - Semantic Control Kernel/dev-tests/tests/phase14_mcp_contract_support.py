from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION

TARGET = {"target_hash": "target_phase14_contract"}
SNAPSHOT = {"state_snapshot_id": "ss_phase14_contract"}


def active_event(tmp_path: Path, tools=("kernel_open_recovery_dialog",)):
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_phase14_contract",
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
    recovery_store.put_recovery_event(
        {
            "allowed_agent_tools": list(tools),
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "target_identity_changed",
            "created_at": utc_iso(),
            "detected_by": "test",
            "expires_at": expires_at,
            "failed_kernel_step": "step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_phase14_contract",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "Target changed.",
            "workflow_run_id": "wr_phase14_contract",
            "workflow_tool": "manual_pipeline_run",
        }
    )
    return paths, mirror.payload["mirror_event_id"], options


def mcp_request(tool_name: str, *, visibility: str, event_scope: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema_version": "semantic_control_kernel.mcp_request.v1",
        "transport": "mcp_server",
        "tool_name": tool_name,
        "visibility": visibility,
        "model_arguments": {},
        "client_context": {
            "host_surface_identity": "test_host",
            "client_request_id": "req_phase14_contract",
        },
        "event_scope": event_scope,
    }
