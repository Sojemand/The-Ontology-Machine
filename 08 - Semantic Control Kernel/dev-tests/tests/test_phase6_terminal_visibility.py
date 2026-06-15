from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_recently_completed_workflow_events_remain_visible_for_completion_relay(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("empty_database_no_semantic_release", TARGET, "phase6_test", workflow_run_id="wr_completed")
    ProgressEventStore(paths).append_progress_event(
        ProgressEvent.from_dict(
            {
                "schema_version": ProgressEvent.SCHEMA_VERSION,
                "workflow_run_id": run.workflow_run_id,
                "workflow_tool": "empty_database_no_semantic_release",
                "step_id": "dc_final_notice",
                "step_label": "dc_final_notice",
                "event_type": "workflow_step",
                "status": "completed",
                "sequence_index": 1,
                "user_visible_summary": "Artifact Tree and empty Corpus DB were created.",
                "current_state_summary": "no_semantic_release",
                "timestamp": "2026-05-10T12:53:31Z",
            }
        )
    )
    KernelMirrorEventService(MirrorEventStore(paths)).create_mirror_event(
        event_type="workflow_completed",
        severity="info",
        user_visible_summary="Artifact Tree and empty Corpus DB were created. No Semantic Release is attached yet.",
        current_state_summary="no_semantic_release",
        mirror_event_id="mev_completed",
        workflow_run_id=run.workflow_run_id,
        workflow_tool="empty_database_no_semantic_release",
        kernel_dialog_state="not_required",
    )
    run_store.mark_run_completed(run.workflow_run_id, "op_completed")

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_completed",
        },
        state_paths=paths,
    )

    event_ids = {event["frontend_event_id"] for event in batch["events"]}
    assert "bridge.progress.wr_completed.000001" in event_ids
    assert "bridge.mirror.mev_completed" in event_ids

def test_recent_terminal_workflow_scope_survives_short_polling_gap(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("manual_pipeline_run", TARGET, "phase6_test", workflow_run_id="wr_recent_gap")
    run_store.mark_run_completed(run.workflow_run_id, "op_recent_gap")
    history_path = paths.workflow_runs_history_dir / f"{run.workflow_run_id}.json"
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    payload["updated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    history_path.write_text(json.dumps(payload), encoding="utf-8")

    assert run.workflow_run_id in recent_terminal_workflow_run_ids(paths)

def test_terminal_workflow_final_mirror_does_not_replay_progress_chain(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("empty_database_custom_taxonomy_custom_projections", TARGET, "phase6_test", workflow_run_id="wr_terminal")
    progress_store = ProgressEventStore(paths)
    for sequence, step_id, status in (
        (1, "tax_analyze_samples", "step_completed"),
        (2, "rel_activate_custom_release", "step_completed"),
        (3, "dc_final_notice", "completed"),
    ):
        progress_store.append_progress_event(
            ProgressEvent.from_dict(
                {
                    "schema_version": ProgressEvent.SCHEMA_VERSION,
                    "workflow_run_id": run.workflow_run_id,
                    "workflow_tool": "empty_database_custom_taxonomy_custom_projections",
                    "step_id": step_id,
                    "step_label": step_id,
                    "event_type": "workflow_step",
                    "status": status,
                    "sequence_index": sequence,
                    "user_visible_summary": f"{step_id} {status}.",
                    "current_state_summary": "semantic_release_active",
                    "timestamp": f"2026-05-10T12:53:3{sequence}Z",
                }
            )
        )
    KernelMirrorEventService(MirrorEventStore(paths)).create_mirror_event(
        event_type="workflow_completed",
        severity="info",
        user_visible_summary="Custom release is active.",
        current_state_summary="semantic_release_active",
        mirror_event_id="mev_terminal_completed",
        workflow_run_id=run.workflow_run_id,
        workflow_tool="empty_database_custom_taxonomy_custom_projections",
        kernel_dialog_state="not_required",
    )
    run_store.mark_run_completed(run.workflow_run_id, "op_terminal")

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "3",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_terminal_final",
        },
        state_paths=paths,
    )

    assert [event["frontend_event_kind"] for event in batch["events"]] == [
        ClientFrontendEventKind.MIRROR_EVENT.value
    ]
    assert batch["events"][0]["frontend_event_id"] == "bridge.mirror.mev_terminal_completed"

def test_mirror_events_use_stable_time_and_do_not_replay_stale_open_dialogs(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    run = WorkflowRunStore(paths).create_run("empty_database_no_semantic_release", TARGET, "phase6_test", workflow_run_id="wr_mirror_time")
    mirror_service = KernelMirrorEventService(MirrorEventStore(paths))
    mirror_service.create_mirror_event(
        event_type="selection_dialog_opened",
        severity="info",
        user_visible_summary="Stable mirror timestamp.",
        current_state_summary="Mirror event is visible through active workflow scope.",
        mirror_event_id="mev_20260526T123456789000Z_stable",
        workflow_run_id=run.workflow_run_id,
        workflow_tool="empty_database_no_semantic_release",
        kernel_dialog_state="not_required",
    )
    mirror_service.create_mirror_event(
        event_type="selection_dialog_opened",
        severity="info",
        user_visible_summary="Old dialog mirror.",
        current_state_summary="Old dialog was already answered.",
        mirror_event_id="mev_20260526T123456789000Z_old_dialog",
        workflow_run_id=run.workflow_run_id,
        workflow_tool="empty_database_no_semantic_release",
        kernel_dialog_state="open",
    )

    request = {
        "schema_version": "semantic_control_kernel.client_events_request.v1",
        "host_surface_identity": "client_frontend_http_pipeline_session",
        "client_instance_id": "browser_1",
        "client_request_id": "req_mirror_time",
    }
    first = list_client_frontend_events(request, state_paths=paths)
    second = list_client_frontend_events({**request, "client_request_id": "req_mirror_time_2"}, state_paths=paths)

    assert "bridge.mirror.mev_20260526T123456789000Z_old_dialog" not in {event["frontend_event_id"] for event in first["events"]}
    first_event = next(event for event in first["events"] if event["frontend_event_id"] == "bridge.mirror.mev_20260526T123456789000Z_stable")
    second_event = next(event for event in second["events"] if event["frontend_event_id"] == "bridge.mirror.mev_20260526T123456789000Z_stable")
    assert first_event["created_at"] == second_event["created_at"]
