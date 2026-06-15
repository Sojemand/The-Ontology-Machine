from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_client_frontend_event_batch_filters_stale_runtime_events_after_active_state_is_gone(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    mirror_store = MirrorEventStore(paths)
    mirror_service = KernelMirrorEventService(mirror_store)

    ProgressEventStore(paths).append_progress_event(
        ProgressEvent.from_dict(
            {
                "schema_version": ProgressEvent.SCHEMA_VERSION,
                "workflow_run_id": "wr_stale",
                "workflow_tool": "manual_pipeline_run",
                "step_id": "step_stale",
                "step_label": "Stale Step",
                "event_type": "workflow_step",
                "status": "step_started",
                "sequence_index": 1,
                "user_visible_summary": "This stale progress event should not be replayed.",
                "current_state_summary": "Stale step started.",
                "timestamp": "2026-05-06T00:00:00Z",
            }
        )
    )
    mirror_service.create_mirror_event(
        event_type="selection_dialog_opened",
        severity="info",
        user_visible_summary="This stale dialog should not be replayed.",
        current_state_summary="Stale dialog state.",
        mirror_event_id="mev_stale",
        workflow_run_id="wr_stale",
        workflow_tool="empty_database_no_semantic_release",
        kernel_dialog_state="open",
    )
    mirror_service.create_mirror_event(
        event_type="llm_validation_failed_final",
        severity="final_error",
        user_visible_summary="Final failure support remains visible while support scope is active.",
        current_state_summary="Support scope is still active.",
        mirror_event_id="mev_support",
        workflow_run_id="wr_support_history",
        workflow_tool="create_custom_projection_path",
        kernel_dialog_state="not_required",
    )
    mirror_store.put_tool_availability(
        "mev_support",
        ["kernel_open_support_bundle"],
        "2099-01-01T00:00:00Z",
    )

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_filter",
        },
        state_paths=paths,
    )

    event_ids = {event["frontend_event_id"] for event in batch["events"]}
    assert "bridge.progress.wr_stale.000001" not in event_ids
    assert "bridge.mirror.mev_stale" not in event_ids
    assert "bridge.mirror.mev_support" in event_ids
    assert "bridge.tool_availability.mev_support" in event_ids

def test_client_frontend_event_batch_treats_kernel_reset_as_visibility_boundary(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    run_store = WorkflowRunStore(paths)
    run = run_store.create_run("create_custom_taxonomy_path", TARGET, "phase6_test", workflow_run_id="wr_before_reset")
    ProgressEventStore(paths).append_progress_event(
        ProgressEvent.from_dict(
            {
                "schema_version": ProgressEvent.SCHEMA_VERSION,
                "workflow_run_id": run.workflow_run_id,
                "workflow_tool": "create_custom_taxonomy_path",
                "step_id": "tax_require_samples",
                "step_label": "tax_require_samples",
                "event_type": "workflow_step",
                "status": "blocked",
                "sequence_index": 1,
                "user_visible_summary": "This pre-reset blocker must not be replayed.",
                "current_state_summary": "blocked",
                "timestamp": "2026-05-10T12:53:31Z",
            }
        )
    )
    mirror_store = MirrorEventStore(paths)
    KernelMirrorEventService(mirror_store).create_mirror_event(
        event_type="recovery_state",
        severity="recoverable_error",
        user_visible_summary="Recovery required before reset.",
        current_state_summary="Pre-reset recovery scope.",
        mirror_event_id="mev_before_reset",
        workflow_run_id=run.workflow_run_id,
        workflow_tool="create_custom_taxonomy_path",
        kernel_dialog_state="not_required",
    )
    mirror_store.put_tool_availability("mev_before_reset", ["kernel_open_recovery_dialog"], "2099-01-01T00:00:00Z")
    run_store.mark_run_completed(run.workflow_run_id, "op_before_reset")

    KernelStateResetService(paths).reset_runtime_state("phase6 reset boundary")

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_after_reset",
        },
        state_paths=paths,
    )

    event_ids = {event["frontend_event_id"] for event in batch["events"]}
    assert "bridge.progress.wr_before_reset.000001" not in event_ids
    assert "bridge.mirror.mev_before_reset" not in event_ids
    assert "bridge.tool_availability.mev_before_reset" not in event_ids
    assert not list(paths.events_tool_availability_dir.glob("*.json"))
