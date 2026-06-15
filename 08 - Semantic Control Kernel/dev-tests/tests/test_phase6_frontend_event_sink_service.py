from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_fake_sink_receives_client_frontend_event(tmp_path: Path) -> None:
    service, sink, _paths = _service(tmp_path)
    run = service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase6_test")

    result = service.request_interaction(
        interaction_function="choose_artifact_root_folder",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_standard_database_workflow",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Choose Artifact Root",
        user_visible_summary="Choose the workspace folder for this database.",
    )

    assert result.ack.payload["accepted"] is True
    assert sink.emitted_events == [result.frontend_event]
    assert result.frontend_event.payload["frontend_event_kind"] == ClientFrontendEventKind.INTERACTION_REQUEST.value
    assert result.frontend_event.payload["interaction_request"]["interaction_request_id"] == result.request.payload["interaction_request_id"]

def test_ack_failure_marks_existing_workflow_waiting(tmp_path: Path) -> None:
    service, _sink, _paths = _service(tmp_path, accepted=False)
    run = service.workflow_run_store.create_run("manual_pipeline_run", TARGET, "phase6_test")

    result = service.request_interaction(
        interaction_function="name_database",
        workflow_run_id=run.workflow_run_id,
        function_or_route="create_empty_database",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Name Database",
        user_visible_summary="Choose the database name.",
    )

    stored_run = service.workflow_run_store.get_run(run.workflow_run_id)
    assert result.ack.payload["accepted"] is False
    assert result.workflow_marked_waiting is True
    assert stored_run.status == "waiting"
    assert stored_run.resume_state_ref.endswith(f"{result.request.payload['interaction_request_id']}.json")

def test_event_sink_has_no_pipeline_adapter_imports() -> None:
    source_path = MODULE_ROOT / "semantic_control_kernel" / "services" / "client_frontend_event_sink.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(".adapters." in module or module.endswith(".adapters") for module in imported_modules)
    assert not any(module.startswith("client_frontend") for module in imported_modules)

def test_client_frontend_event_batch_includes_persisted_progress_events(tmp_path: Path) -> None:
    _kernel_service, _sink, paths = _service(tmp_path)
    WorkflowRunStore(paths).create_run("manual_pipeline_run", TARGET, "phase6_test", workflow_run_id="wr_progress")
    progress = ProgressEvent.from_dict(
        {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": "wr_progress",
            "workflow_tool": "manual_pipeline_run",
            "step_id": "step_1",
            "step_label": "Step 1",
            "event_type": "workflow_step",
            "status": "step_started",
            "sequence_index": 1,
            "user_visible_summary": "Kernel progress should be visible to the frontend.",
            "current_state_summary": "Step 1 started.",
            "timestamp": "2026-05-06T00:00:00Z",
        }
    )
    ProgressEventStore(paths).append_progress_event(progress)

    batch = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_1",
        },
        state_paths=paths,
    )

    assert [event["frontend_event_kind"] for event in batch["events"]] == [ClientFrontendEventKind.PROGRESS_EVENT.value]
    assert batch["events"][0]["progress_event"]["workflow_run_id"] == "wr_progress"
    overrun = list_client_frontend_events(
        {
            "schema_version": "semantic_control_kernel.client_events_request.v1",
            "cursor": "99",
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_instance_id": "browser_1",
            "client_request_id": "req_cursor_overrun",
        },
        state_paths=paths,
    )
    assert overrun["events"][0]["frontend_event_id"] == "bridge.progress.wr_progress.000001"
