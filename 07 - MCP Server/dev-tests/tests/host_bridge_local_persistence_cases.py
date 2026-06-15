from __future__ import annotations

from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.surface.client_frontend_bridge import (
    cancel_user_interaction,
    list_client_frontend_events,
    submit_user_interaction_response,
)

from .host_bridge_support import SNAPSHOT, TARGET, service, submit_request


def test_host_only_bridge_reads_events_and_persists_submit_and_cancel(tmp_path) -> None:
    paths, dispatch = service(tmp_path)
    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "",
            "limit": 10,
            "host_surface_identity": "test_frontend",
            "client_instance_id": "client_a",
            "client_request_id": "req_events",
        },
        state_paths=paths,
    )
    assert batch["schema_version"] == "kernel.client_frontend_event_batch.v1"
    assert batch["events"]

    submit = submit_user_interaction_response(
        submit_request(dispatch.request.payload["interaction_request_id"]),
        state_paths=paths,
    )
    assert submit["status"] == "accepted"
    assert submit["persisted_response"]["schema_version"] == "kernel.user_interaction_response.v1"

    paths_cancel, dispatch_cancel = service(tmp_path / "cancel")
    cancelled = cancel_user_interaction(
        {
            "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
            "interaction_request_id": dispatch_cancel.request.payload["interaction_request_id"],
            "response_status": "cancelled",
            "target_identity": TARGET,
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "test_frontend",
            "client_request_id": "req_cancel",
            "cancellation_reason": "user_cancelled",
        },
        state_paths=paths_cancel,
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["persisted_response"]["response_status"] == "cancelled"


def test_host_bridge_rejects_stale_identities(tmp_path) -> None:
    paths, dispatch = service(tmp_path)
    stale = submit_user_interaction_response(
        {
            "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
            "interaction_request_id": dispatch.request.payload["interaction_request_id"],
            "response": {
                "schema_version": "kernel.user_interaction_response.v1",
                "interaction_response_id": "resp_stale",
                "interaction_request_id": dispatch.request.payload["interaction_request_id"],
                "response_status": "submitted",
                "target_identity": {"target_hash": "wrong"},
                "state_snapshot_identity": SNAPSHOT,
                "host_surface_identity": "test_frontend",
                "submitted_at": utc_iso(),
                "text_value": "Wrong DB",
            },
            "target_identity": {"target_hash": "wrong"},
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "test_frontend",
            "client_request_id": "req_stale",
        },
        state_paths=paths,
    )
    assert stale["status"] == "rejected_stale"
