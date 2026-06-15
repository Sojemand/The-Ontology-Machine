from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_bridge_closed_interaction_defaults_to_user_closed_reason(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase6_test")
    request = service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_standard_database_workflow",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Artifact Root",
        user_visible_summary="Choose the workspace folder for this database.",
    ).request

    response = cancel_user_interaction(
        {
            "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response_status": "closed",
            "target_identity": request.payload["target_identity"],
            "state_snapshot_identity": request.payload["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_request_id": "req_close",
        },
        state_paths=paths,
    )

    assert response["status"] == "closed"
    assert response["persisted_response"]["cancellation_reason"] == "user_closed_dialog"

def test_bridge_expired_interaction_defaults_to_timeout_reason(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase6_test")
    request = service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_standard_database_workflow",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Artifact Root",
        user_visible_summary="Choose the workspace folder for this database.",
    ).request

    response = cancel_user_interaction(
        {
            "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response_status": "expired",
            "target_identity": request.payload["target_identity"],
            "state_snapshot_identity": request.payload["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_request_id": "req_expired",
        },
        state_paths=paths,
    )

    assert response["status"] == "expired"
    assert response["persisted_response"]["cancellation_reason"] == "timeout"

def test_bridge_stale_cancel_reports_rejected_stale_not_false_cancelled(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase6_test")
    request = service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_standard_database_workflow",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Artifact Root",
        user_visible_summary="Choose the workspace folder for this database.",
    ).request

    response = cancel_user_interaction(
        {
            "schema_version": "semantic_control_kernel.interaction_cancel_request.v1",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response_status": "cancelled",
            "target_identity": {"target_hash": "different"},
            "state_snapshot_identity": request.payload["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_request_id": "req_cancel",
            "cancellation_reason": "user_cancelled",
        },
        state_paths=paths,
    )

    assert response["status"] == "rejected_stale"
    assert response["error"]["code"] == "target_identity_changed"
