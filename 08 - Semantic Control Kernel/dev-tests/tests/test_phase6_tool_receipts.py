from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_client_event_batch_includes_event_scoped_tool_availability(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    service.request_recovery_dialog(
        recovery_dialog_type="stale_lock_dialog",
        recovery_id="rcv_phase6_tools",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_recovery_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Recovery",
        user_visible_summary="A stale lock recovery dialog is available.",
        user_visible_cause="A lock may be stale.",
        recovery_effect="The Kernel can reopen the stale lock dialog.",
        risk_class="read_only",
        options=(
            {
                "schema_version": "kernel.recovery_option.v1",
                "recovery_id": "rcv_phase6_tools",
                "recovery_event_id": "rev_phase6_tools",
                "label": "Open recovery dialog",
                "description": "Reopen the stale lock recovery dialog.",
                "owner": "agent_tool",
                "recovery_action_type": "reopen_dialog",
                "effect": "open_kernel_recovery_dialog",
                "risk_class": "read_only",
                "target_identity": TARGET,
                "state_snapshot_identity": SNAPSHOT,
                "agent_tool": "kernel_open_recovery_dialog",
                "kernel_dialog_action": "stale_lock_dialog",
                "starts_new_workflow": False,
                "continuation_workflow_tool": None,
                "requires_confirmation": False,
                "expires_at": "2026-05-06T00:30:00Z",
            },
        ),
        allowed_agent_tools=("kernel_open_recovery_dialog",),
    )

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_tools",
        },
        state_paths=paths,
    )

    tool_events = [
        event
        for event in batch["events"]
        if event["frontend_event_kind"] == ClientFrontendEventKind.TOOL_AVAILABILITY.value
    ]
    assert tool_events
    assert tool_events[0]["tool_availability"]["allowed_agent_tools"] == ["kernel_open_recovery_dialog"]

def test_confirmation_response_appends_confirmation_receipt(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    receipt_store = ReceiptStore(paths)
    service = KernelUserInteractionService(
        interaction_store=InteractionRequestStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        event_sink=FakeClientFrontendSink(),
        workflow_run_store=WorkflowRunStore(paths),
        receipt_store=receipt_store,
    )
    run = service.workflow_run_store.create_run("reset_database", TARGET, "phase6_test")
    request = service.request_interaction(
        interaction_function="user_confirmation",
        workflow_run_id=run.workflow_run_id,
        function_or_route="reset_database",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Confirm Reset",
        user_visible_summary="Confirm the destructive reset for the selected database.",
        risk_class="destructive",
        confirmation_request_id="cfq_phase6_reset",
    ).request

    response = UserInteractionResponse.from_dict(
        {
            "schema_version": UserInteractionResponse.SCHEMA_VERSION,
            "interaction_response_id": "irs_confirm_reset",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response_status": "submitted",
            "confirmation_decision": "confirmed",
            "target_identity": request.payload["target_identity"],
            "state_snapshot_identity": request.payload["state_snapshot_identity"],
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "submitted_at": "2026-05-06T00:00:00Z",
        }
    )

    result = service.submit_response(response)
    receipt = receipt_store.get_receipt(result.confirmation_receipt.payload["confirmation_receipt_id"])

    assert result.confirmation_receipt.payload["confirmation_request_id"] == "cfq_phase6_reset"
    assert receipt.payload["confirmed_target_identity"] == TARGET
