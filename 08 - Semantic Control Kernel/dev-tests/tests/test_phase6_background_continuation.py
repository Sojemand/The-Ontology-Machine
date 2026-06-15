from __future__ import annotations

from phase6_frontend_event_sink_support import *  # noqa: F403

def test_submit_interaction_response_can_launch_background_continuation(tmp_path: Path) -> None:
    service, _sink, paths = _service(tmp_path)
    run = service.workflow_run_store.create_run(
        "empty_database_default_taxonomy_custom_projections",
        TARGET,
        "phase6_test",
        workflow_run_id="wr_background_continue",
    )
    request = service.request_interaction(
        interaction_function="name_database",
        workflow_run_id=run.workflow_run_id,
        function_or_route="empty_database_default_taxonomy_custom_projections",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Name Database",
        user_visible_summary="Enter database name.",
    ).request
    launches: list[dict[str, object]] = []

    def fake_launcher(**kwargs):
        launches.append(dict(kwargs))
        return {
            "schema_version": "kernel.background_continuation_ref.v1",
            "launch_id": "bgc_test",
            "mode": "background_process",
            "pid": 123,
            "workflow_run_id": kwargs["workflow_run_id"],
            "workflow_tool": kwargs["workflow_tool"],
            "started_at": "2026-05-06T00:00:00Z",
            "stdout_ref": "debug/background_continuations/wr_background_continue/bgc_test.stdout.json",
            "stderr_ref": "debug/background_continuations/wr_background_continue/bgc_test.stderr.txt",
        }

    response = submit_user_interaction_response(
        {
            "schema_version": "semantic_control_kernel.interaction_response_submit.v1",
            "interaction_request_id": request.payload["interaction_request_id"],
            "response": {
                "schema_version": UserInteractionResponse.SCHEMA_VERSION,
                "interaction_response_id": "irs_background_continue",
                "interaction_request_id": request.payload["interaction_request_id"],
                "response_status": "submitted",
                "target_identity": TARGET,
                "state_snapshot_identity": SNAPSHOT,
                "host_surface_identity": "client_frontend_http_pipeline_session",
                "submitted_at": "2026-05-06T00:00:00Z",
                "text_value": "Background DB",
            },
            "target_identity": TARGET,
            "state_snapshot_identity": SNAPSHOT,
            "host_surface_identity": "client_frontend_http_pipeline_session",
            "client_request_id": "req_submit_background",
        },
        state_paths=paths,
        continue_inline=False,
        background_launcher=fake_launcher,
    )

    assert response["status"] == "accepted"
    assert response["background_continuation"]["workflow_run_id"] == run.workflow_run_id
    assert "continued_workflow_result" not in response
    assert launches[0]["workflow_run_id"] == run.workflow_run_id
    assert WorkflowRunStore(paths).get_run(run.workflow_run_id).status == "running"
    progress_events = ProgressEventStore(paths).list_progress_events(run.workflow_run_id)
    progress = progress_events[-1].to_dict()
    assert progress["step_id"] == "kernel_background_continuation"
    assert progress["current_state_summary"] == "unknown"

def test_background_continuation_terminal_progress_closes_started_marker(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")

    append_background_continuation_progress(
        paths,
        workflow_run_id="wr_background_terminal",
        workflow_tool="database_merge_additive_only",
    )
    append_background_continuation_terminal_progress(
        paths,
        workflow_run_id="wr_background_terminal",
        workflow_tool="database_merge_additive_only",
        result_status="ok",
        current_state_summary="workflow_completed",
    )

    progress_events = [event.to_dict() for event in ProgressEventStore(paths).list_progress_events("wr_background_terminal")]

    assert [event["step_id"] for event in progress_events] == [
        "kernel_background_continuation",
        "kernel_background_continuation",
    ]
    assert [event["status"] for event in progress_events] == ["step_started", "completed"]
    assert [event["sequence_index"] for event in progress_events] == [1, 2]
    assert progress_events[-1]["current_state_summary"] == "workflow_completed"

def test_auto_continuation_policy_only_inlines_short_target_dialogs() -> None:
    assert bridge_module._should_continue_inline({"interaction_function": "choose_artifact_root_folder"}, None)
    assert bridge_module._should_continue_inline({"interaction_function": "name_artifact_root_folder"}, None)
    assert bridge_module._should_continue_inline({"interaction_function": "choose_merge_database_count"}, None)
    assert bridge_module._should_continue_inline({"interaction_function": "choose_databases_to_merge"}, None)
    assert not bridge_module._should_continue_inline({"interaction_function": "name_database"}, None)
    assert not bridge_module._should_continue_inline({"interaction_function": "select_sample_files"}, None)
    assert bridge_module._should_continue_inline({"interaction_function": "choose_new_artifact_root_folder"}, None)
    assert not bridge_module._should_continue_inline({"interaction_function": "choose_merge_projection_mode"}, None)

def test_background_continuation_launcher_uses_kernel_contract_and_state_override(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths(module_root=MODULE_ROOT, state_root=tmp_path / "state")
    paths.ensure_layout()
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 456

    def fake_popen(command, **kwargs):
        captured["command"] = list(command)
        captured["kwargs"] = dict(kwargs)
        return FakeProcess()

    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.subprocess.Popen", fake_popen)

    ref = launch_interaction_continuation(
        state_paths=paths,
        workflow_run_id="wr_launcher",
        workflow_tool="empty_database_default_taxonomy_custom_projections",
    )

    command = captured["command"]
    kwargs = captured["kwargs"]
    assert command[1:4] == ["-m", "semantic_control_kernel.orchestrator_contract", "continue-after-interaction"]
    assert "--workflow-run-id" in command
    assert kwargs["cwd"] == MODULE_ROOT
    assert kwargs["close_fds"] is True
    assert kwargs["env"]["VISION_KERNEL_STATE_ROOT"] == str(paths.state_root)
    assert ref["pid"] == 456
    assert ref["stdout_ref"].startswith("debug/background_continuations/wr_launcher/")
    ref_path = paths.state_root / ref["process_ref"]
    stored_ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert stored_ref["pid"] == 456
    assert stored_ref["workflow_run_id"] == "wr_launcher"

def test_background_continuation_termination_uses_persisted_process_refs(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths(module_root=MODULE_ROOT, state_root=tmp_path / "state")
    paths.ensure_layout()
    ref_dir = paths.debug_background_continuations_dir / "wr_cancel"
    ref_dir.mkdir(parents=True)
    ref_path = ref_dir / "bgc_cancel.ref.json"
    ref_path.write_text(
        json.dumps(
            {
                "schema_version": "kernel.background_continuation_ref.v1",
                "launch_id": "bgc_cancel",
                "mode": "background_process",
                "pid": 789,
                "workflow_run_id": "wr_cancel",
                "workflow_tool": "manual_pipeline_run",
                "started_at": "2026-05-06T00:00:00Z",
                "stdout_ref": "debug/background_continuations/wr_cancel/bgc_cancel.stdout.json",
                "stderr_ref": "debug/background_continuations/wr_cancel/bgc_cancel.stderr.txt",
                "process_ref": "debug/background_continuations/wr_cancel/bgc_cancel.ref.json",
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = "terminated"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = list(command)
        captured["kwargs"] = dict(kwargs)
        return Completed()

    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.os.name", "nt")
    monkeypatch.setattr("semantic_control_kernel.surface.background_continuation.subprocess.run", fake_run)

    result = terminate_background_continuations(paths, workflow_run_ids=["wr_cancel"])

    assert captured["command"][:4] == ["taskkill", "/PID", "789", "/T"]
    assert result["ref_count"] == 1
    assert result["terminated"][0]["pid"] == 789
    assert result["failed"] == []
