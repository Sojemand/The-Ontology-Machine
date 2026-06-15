from __future__ import annotations

from pathlib import Path

import pytest

from phase6_recovery_dialog_support import SNAPSHOT, TARGET, recovery_option, service_for, service_with_paths
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.validation.contract_validation import KernelContractError


def test_recovery_dialog_submission_expires_event_scoped_tool_availability(tmp_path: Path) -> None:
    service, _paths, mirror_store = service_with_paths(tmp_path)
    result = service.request_recovery_dialog(
        recovery_dialog_type="stale_lock_dialog",
        recovery_id="rcv_stale_lock",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_recovery_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Recovery",
        user_visible_summary="A safe recovery decision is required.",
        user_visible_cause="A lock may be stale.",
        recovery_effect="The selected recovery path will be validated before any state changes.",
        risk_class="read_only",
        options=[
            recovery_option(
                "rcv_stale_lock",
                "stale_lock_dialog",
                label="Open recovery dialog",
                description="Reopen the stale lock recovery dialog.",
                agent_tool="kernel_open_recovery_dialog",
                owner="agent_tool",
            )
        ],
        allowed_agent_tools=("kernel_open_recovery_dialog",),
    )
    availability = mirror_store.get_tool_availability(result.mirror_event.payload["mirror_event_id"])
    assert availability.payload["status"] == "active"

    response = UserInteractionResponse.from_dict(
        {
            "choice_id": "inspect_status",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "interaction_request_id": result.request.payload["interaction_request_id"],
            "interaction_response_id": "irs_stale_lock_choice",
            "recovery_id": result.request.payload["recovery_id"],
            "response_status": "submitted",
            "schema_version": UserInteractionResponse.SCHEMA_VERSION,
            "state_snapshot_identity": result.request.payload["state_snapshot_identity"],
            "submitted_at": "2026-05-05T00:00:00Z",
            "target_identity": result.request.payload["target_identity"],
        }
    )

    submit_result = service.submit_response(response)
    expired = mirror_store.get_tool_availability(result.mirror_event.payload["mirror_event_id"])

    assert submit_result.accepted is True
    assert expired.payload["status"] == "expired"
    assert expired.payload["reason"] == "resolved"


def test_recovery_dialogs_require_their_mapped_value_not_only_recovery_id(tmp_path: Path) -> None:
    service = service_for(tmp_path)
    result = service.request_recovery_dialog(
        recovery_dialog_type="stale_lock_dialog",
        recovery_id="rcv_stale_lock",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_recovery_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Recovery",
        user_visible_summary="A safe recovery decision is required.",
        user_visible_cause="A lock may be stale.",
        recovery_effect="The selected recovery path will be validated before any state changes.",
        risk_class="read_only",
        options=[
            recovery_option(
                "rcv_stale_lock",
                "stale_lock_dialog",
                label="Inspect",
                description="Inspect the stale lock recovery dialog.",
            )
        ],
    )

    response = UserInteractionResponse.from_dict(
        {
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "interaction_request_id": result.request.payload["interaction_request_id"],
            "interaction_response_id": "irs_stale_lock_missing_choice",
            "recovery_id": result.request.payload["recovery_id"],
            "response_status": "submitted",
            "schema_version": UserInteractionResponse.SCHEMA_VERSION,
            "state_snapshot_identity": result.request.payload["state_snapshot_identity"],
            "submitted_at": "2026-05-05T00:00:00Z",
            "target_identity": result.request.payload["target_identity"],
        }
    )

    with pytest.raises(KernelContractError):
        service.submit_response(response)
