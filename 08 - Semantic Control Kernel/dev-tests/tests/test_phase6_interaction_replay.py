from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_submitted_active_interaction_record_is_not_replayed_as_live_dialog(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("empty_database_no_semantic_release", TARGET, "phase6_test", workflow_run_id="wr_submitted")
    request = service.request_interaction(
        interaction_function="name_database",
        workflow_run_id=run.workflow_run_id,
        function_or_route="empty_database_no_semantic_release",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Name Database",
        user_visible_summary="Enter the database name.",
    ).request
    response = UserInteractionResponse.from_dict(
        {
            "schema_version": UserInteractionResponse.SCHEMA_VERSION,
            "interaction_response_id": "irs_submitted",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response_status": "submitted",
            "target_identity": request.payload["target_identity"],
            "state_snapshot_identity": request.payload["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "submitted_at": "2026-05-10T13:17:12Z",
            "text_value": "Artifact Tree Kernel Test",
        }
    )
    service.interaction_store.submit_interaction_response(response)
    history_path = paths.pending_interactions_history_dir / f"{request.payload['interaction_request_id']}.json"
    active_path = paths.pending_interactions_active_dir / f"{request.payload['interaction_request_id']}.json"
    active_path.write_text(history_path.read_text(encoding="utf-8"), encoding="utf-8")

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_submitted_replay",
        },
        state_paths=paths,
    )

    assert not any(event["frontend_event_kind"] == ClientFrontendEventKind.INTERACTION_REQUEST.value for event in batch["events"])

def test_active_pending_interaction_is_replayed_when_cursor_skips_it(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("empty_database_no_semantic_release", TARGET, "phase6_test", workflow_run_id="wr_cursor")
    request = service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=run.workflow_run_id,
        function_or_route="empty_database_no_semantic_release",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Artifact Root",
        user_visible_summary="Choose the workspace folder for this database.",
    ).request

    skipped_batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_cursor_skipped",
        },
        state_paths=paths,
    )
    overflow_batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "99",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_cursor_overflow",
        },
        state_paths=paths,
    )

    for batch in (skipped_batch, overflow_batch):
        interaction_events = [
            event
            for event in batch["events"]
            if event["frontend_event_kind"] == ClientFrontendEventKind.INTERACTION_REQUEST.value
        ]
        assert [event["interaction_request"]["interaction_request_id"] for event in interaction_events] == [
            request.payload["interaction_request_id"]
        ]

def test_active_progress_chain_is_replayed_when_cursor_is_caught_up(tmp_path: Path) -> None:
    _service_obj, _sink, paths = _service(tmp_path)
    WorkflowRunStore(paths).create_run("empty_database_custom_taxonomy_no_projections", TARGET, "phase6_test", workflow_run_id="wr_progress_replay")
    store = ProgressEventStore(paths)
    for sequence, step_id, status, summary in (
        (1, "tax_require_samples", "waiting_for_user", "Waiting for taxonomy samples."),
        (2, "tax_analyze_samples", "step_started", "Taxonomy sample analysis started."),
    ):
        store.append_progress_event(
            ProgressEvent.from_dict(
                {
                    "schema_version": ProgressEvent.SCHEMA_VERSION,
                    "workflow_run_id": "wr_progress_replay",
                    "workflow_tool": "empty_database_custom_taxonomy_no_projections",
                    "step_id": step_id,
                    "step_label": step_id,
                    "event_type": "workflow_step",
                    "status": status,
                    "sequence_index": sequence,
                    "user_visible_summary": summary,
                    "current_state_summary": "no_semantic_release",
                    "timestamp": f"2026-05-06T00:00:0{sequence}Z",
                }
            )
        )

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "2",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_progress_replay",
        },
        state_paths=paths,
    )

    progress_events = [
        event["progress_event"]
        for event in batch["events"]
        if event["frontend_event_kind"] == ClientFrontendEventKind.PROGRESS_EVENT.value
    ]
    assert [(event["step_id"], event["status"], event["sequence_index"]) for event in progress_events] == [
        ("tax_require_samples", "waiting_for_user", 1),
        ("tax_analyze_samples", "step_started", 2),
    ]
