from __future__ import annotations

from pathlib import Path

from phase14_mcp_contract_support import RECOVERY_EVENT_SCHEMA_VERSION, SNAPSHOT, TARGET, active_event, mcp_request
from semantic_control_kernel import mcp_contract
from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.types.enums import RecoveryStateClass
from semantic_control_kernel.types.events import MirrorEvent


def test_event_scoped_mcp_call_rejects_missing_recovery_binding_fields(tmp_path: Path, monkeypatch) -> None:
    paths, mirror_event_id, _options = active_event(tmp_path)
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(paths.state_root))

    response = mcp_contract.call_mcp_tool(
        mcp_request(
            "kernel_open_recovery_dialog",
            visibility="event_scoped",
            event_scope={
                "mirror_event_id": mirror_event_id,
                "recovery_event_id": "rev_phase14_contract",
                "state_snapshot_id": "ss_phase14_contract",
                "client_request_id": "req_phase14_contract",
            },
        )
    )

    assert response["status"] == "failed"
    assert response["error"]["code"] == "event_scoped_tool_not_available"


def test_event_scoped_mcp_call_requires_recovery_bound_mirror_event(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    mirror_store = MirrorEventStore(paths)
    recovery_store = RecoveryEventStore(paths)
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_bad_mirror",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        expires_at=expires_at,
        safe_tools=("kernel_open_recovery_dialog",),
    )
    mirror_store.append_mirror_event(
        MirrorEvent.from_dict(
            {
                "schema_version": "kernel.mirror_event.v1",
                "mirror_event_id": "mirror_bad",
                "mirror_source": "kernel",
                "is_kernel_auto_call": True,
                "event_type": "recovery_state",
                "severity": "recoverable_error",
                "user_visible_summary": "Thin mirror lacks recovery bindings.",
                "current_state_summary": "Recovery is active.",
            }
        )
    )
    mirror_store.put_tool_availability("mirror_bad", ["kernel_open_recovery_dialog"], expires_at)
    recovery_store.put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_open_recovery_dialog"],
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "target_identity_changed",
            "created_at": utc_iso(),
            "detected_by": "test",
            "expires_at": expires_at,
            "failed_kernel_step": "step",
            "mirror_event_id": "mirror_bad",
            "recovery_event_id": "rev_bad_mirror",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": SNAPSHOT,
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": TARGET,
            "user_visible_cause": "Target changed.",
            "workflow_run_id": "wr_bad_mirror",
            "workflow_tool": "manual_pipeline_run",
        }
    )
    monkeypatch.setenv("VISION_KERNEL_STATE_ROOT", str(paths.state_root))

    response = mcp_contract.call_mcp_tool(
        mcp_request(
            "kernel_open_recovery_dialog",
            visibility="event_scoped",
            event_scope={
                "mirror_event_id": "mirror_bad",
                "recovery_event_id": "rev_bad_mirror",
                "state_snapshot_id": "ss_phase14_contract",
                "client_request_id": "req_phase14_contract",
                "recovery_id": options[0].payload["recovery_id"],
                "tool_call_nonce": "nonce_bad_mirror",
            },
        )
    )

    assert response["status"] == "failed"
    assert response["error"]["code"] == "event_scoped_tool_not_available"
