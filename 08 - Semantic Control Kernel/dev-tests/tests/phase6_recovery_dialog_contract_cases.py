from __future__ import annotations

from pathlib import Path

import pytest

from phase6_recovery_dialog_support import (
    SNAPSHOT,
    TARGET,
    recovery_option,
    service_for,
    value_for_recovery_type,
)
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.types.interaction import RECOVERY_DIALOG_MAPPINGS


@pytest.mark.parametrize("recovery_dialog_type", sorted(RECOVERY_DIALOG_MAPPINGS))
def test_recovery_dialogs_preserve_recovery_id_target_and_snapshot(tmp_path: Path, recovery_dialog_type: str) -> None:
    service = service_for(tmp_path)
    result = service.request_recovery_dialog(
        recovery_dialog_type=recovery_dialog_type,
        recovery_id=f"rcv_{recovery_dialog_type}",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_recovery_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Recovery",
        user_visible_summary="A safe recovery decision is required.",
        user_visible_cause="The Kernel detected a recoverable state.",
        recovery_effect="The selected recovery path will be validated before any state changes.",
        risk_class="read_only",
        options=[
            recovery_option(
                f"rcv_{recovery_dialog_type}",
                recovery_dialog_type,
                label="Continue",
                description="Continue with the Kernel-provided recovery dialog.",
            )
        ],
    )

    response_payload = {
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "interaction_request_id": result.request.payload["interaction_request_id"],
        "interaction_response_id": f"irs_{recovery_dialog_type}",
        "recovery_id": result.request.payload["recovery_id"],
        "response_status": "submitted",
        "schema_version": UserInteractionResponse.SCHEMA_VERSION,
        "state_snapshot_identity": result.request.payload["state_snapshot_identity"],
        "submitted_at": "2026-05-05T00:00:00Z",
        "target_identity": result.request.payload["target_identity"],
    }
    response_payload.update(value_for_recovery_type(recovery_dialog_type))
    response = UserInteractionResponse.from_dict(response_payload)
    submit_result = service.submit_response(response)

    assert submit_result.accepted is True
    assert submit_result.consumed_value is True
    assert response.payload["recovery_id"] == result.request.payload["recovery_id"]
    assert response.payload["target_identity"] == result.request.payload["target_identity"]
    assert response.payload["state_snapshot_identity"] == result.request.payload["state_snapshot_identity"]
