from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

from mcp_server.semantic_control_kernel_visibility import authorize_tool_call


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
KERNEL_ROOT = PIPELINE_ROOT / "08 - Semantic Control Kernel"
if str(KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(KERNEL_ROOT))

from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService  # noqa: E402
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy  # noqa: E402
from semantic_control_kernel.repository.event_store import MirrorEventStore  # noqa: E402
from semantic_control_kernel.repository.paths import StatePaths, utc_iso  # noqa: E402
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore  # noqa: E402
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService  # noqa: E402
from semantic_control_kernel.surface.client_frontend_bridge import list_event_scoped_tool_definitions  # noqa: E402
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass  # noqa: E402
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION  # noqa: E402


DRIFT_PREFLIGHT_STATUS = "drift_preflight: build_plan_authority_applied"
DRIFT_PREFLIGHT_DETAIL = (
    "Phase 14 tool-definition lookup stays keyed by mirror_event_id/recovery_event_id/state_snapshot_id/client_request_id, while concrete recovery-tool calls still require recovery_id-bound hidden scope."
)

TARGET = {"target_hash": "target_phase14"}
SNAPSHOT = {"state_snapshot_id": "ss_phase14"}


def _active_event(
    tmp_path: Path,
    tools=("kernel_open_recovery_dialog", "kernel_open_support_bundle"),
    *,
    expires_at: str | None = None,
):
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)
    expires_at = expires_at or RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_phase14",
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
            "recovery_event_id": "rev_phase14",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "Target changed.",
            "workflow_run_id": "wr_phase14",
            "workflow_tool": "manual_pipeline_run",
        }
    )
    return paths, mirror.payload["mirror_event_id"], expires_at, options[0].payload["recovery_id"]


def test_event_scoped_tool_definitions_follow_active_kernel_recovery_scope(tmp_path: Path, monkeypatch) -> None:
    assert DRIFT_PREFLIGHT_STATUS == "drift_preflight: build_plan_authority_applied"
    assert "recovery_id" in DRIFT_PREFLIGHT_DETAIL

    paths, mirror_event_id, _expires_at, recovery_id = _active_event(tmp_path)
    payload = list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_phase14",
            "host_surface_identity": "test",
            "client_request_id": "req_phase14",
        },
        state_paths=paths,
    )

    assert payload["status"] == "active"
    assert [tool["name"] for tool in payload["tool_definitions"]] == [
        "kernel_open_recovery_dialog",
        "kernel_open_support_bundle",
    ]

    monkeypatch.setattr(
        "mcp_server.semantic_control_kernel_client.SemanticControlKernelClient.list_event_scoped_tool_definitions",
        lambda _self, _request: payload,
    )

    guarded = authorize_tool_call(
        "kernel_open_recovery_dialog",
        {
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_phase14",
            "client_request_id": "req_phase14",
            "recovery_id": recovery_id,
            "tool_call_nonce": "nonce_phase14",
        },
    )
    assert guarded["response"] is None
    assert guarded["enforce_permissions"] is False


def test_stale_or_resolved_event_scoped_requests_fail_closed(tmp_path: Path) -> None:
    paths, mirror_event_id, _expires_at, _recovery_id = _active_event(tmp_path)
    recovery_store = RecoveryEventStore(paths)
    mirror_store = MirrorEventStore(paths)

    mismatch = list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_wrong",
            "host_surface_identity": "test",
            "client_request_id": "req_phase14",
        },
        state_paths=paths,
    )
    assert mismatch["status"] == "failed"

    mirror_store.mark_event_scoped_tools_expired(mirror_event_id, "resolved")
    expired = list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_phase14",
            "host_surface_identity": "test",
            "client_request_id": "req_phase14",
        },
        state_paths=paths,
    )
    assert expired["status"] == "expired"

    recovery_store.update_status("rev_phase14", "superseded", superseded_by="rev_new")
    superseded = list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_phase14",
            "host_surface_identity": "test",
            "client_request_id": "req_phase14",
        },
        state_paths=paths,
    )
    assert superseded["status"] in {"failed", "expired", "superseded"}


def test_expired_event_scoped_availability_returns_typed_expired_response(tmp_path: Path) -> None:
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    paths, mirror_event_id, _expires_at, _recovery_id = _active_event(tmp_path, expires_at=past)

    expired = list_event_scoped_tool_definitions(
        {
            "schema_version": "semantic_control_kernel.event_scoped_tool_definitions_request.v1",
            "mirror_event_id": mirror_event_id,
            "recovery_event_id": "rev_phase14",
            "state_snapshot_id": "ss_phase14",
            "host_surface_identity": "test",
            "client_request_id": "req_phase14",
        },
        state_paths=paths,
    )

    assert expired["status"] == "expired"
    assert expired["tool_definitions"] == []
    assert expired["error"]["code"] == "event_scope_expired"
