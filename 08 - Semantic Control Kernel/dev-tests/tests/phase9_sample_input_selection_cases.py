from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.events import UserInteractionResponse
from semantic_control_kernel.workflows.database_creation.interaction_port import DatabaseCreationInteractionPort
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow

from _phase9_fakes import FakeLLMPort, runtime_for, target_for
from phase9_sample_input_support import FakeOrchestratorAdapter


def test_select_sample_files_waits_then_builds_analyze_input_from_optimizer_raw(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    target = target_for(tmp_path)
    input_root = Path(target.input_path)
    input_root.mkdir(parents=True)
    source = input_root / "invoice sample.txt"
    source.write_text("Rechnung RE-2026-001", encoding="utf-8")
    adapter = FakeOrchestratorAdapter(tmp_path / "optimizer_raw")
    port = DatabaseCreationInteractionPort(paths, orchestrator_adapter=adapter)

    first = port.select_sample_files(
        workflow_tool="empty_database_default_taxonomy_custom_projections",
        workflow_run_id="wr_samples",
        purpose="projection",
        target=target,
    )

    assert first == ()
    request = port.pending_sample_files_request("wr_samples")
    assert request is not None
    assert request.payload["interaction_function"] == "select_sample_files"

    port.user_interaction_service.submit_response(
        UserInteractionResponse.from_dict(
            {
                "schema_version": UserInteractionResponse.SCHEMA_VERSION,
                "interaction_response_id": "irs_samples_present",
                "interaction_request_id": request.payload["interaction_request_id"],
                "response_status": "submitted",
                "confirmation_decision": "confirmed",
                "target_identity": request.payload["target_identity"],
                "state_snapshot_identity": request.payload["state_snapshot_identity"],
                "host_surface_identity": "phase9_test",
                "submitted_at": "2026-05-26T00:00:00Z",
            }
        )
    )

    refs = port.select_sample_files(
        workflow_tool="empty_database_default_taxonomy_custom_projections",
        workflow_run_id="wr_samples",
        purpose="projection",
        target=target,
    )

    assert adapter.requests[0]["source_document_path"] == str(source.resolve(strict=False))
    sample_input = refs[0]["analyze_sample_input"]
    assert len(refs) == 1
    assert sample_input["schema_version"] == "kernel.analyze_sample.input.v1"
    assert sample_input["source_ref"]["kind"] == "interpreter_request_view_file.v1"
    assert sample_input["route"]["interpreter_profile"] == "file"
    assert sample_input["document"]["extracted_content"]["sections"][0]["text"] == "Rechnung RE-2026-001"


def test_sample_confirmation_continue_reuses_progress_state(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    target = target_for(tmp_path)
    port = DatabaseCreationInteractionPort(
        paths,
        orchestrator_adapter=FakeOrchestratorAdapter(tmp_path / "optimizer_raw"),
    )
    runtime = runtime_for(tmp_path, target=target, llm_port=FakeLLMPort())
    runtime.interaction_port = port

    initial = run_database_creation_workflow(
        "empty_database_default_taxonomy_custom_projections",
        runtime=runtime,
        workflow_run_id="wr_sample_continue",
        target=target,
    )

    assert initial.status == "waiting"
    assert initial.blocked_step_id == "proj_require_samples"
    source = Path(target.input_path) / "invoice sample.txt"
    source.write_text("Rechnung RE-2026-001", encoding="utf-8")
    request = port.pending_sample_files_request("wr_sample_continue")
    assert request is not None
    port.user_interaction_service.submit_response(
        UserInteractionResponse.from_dict(
            {
                "schema_version": UserInteractionResponse.SCHEMA_VERSION,
                "interaction_response_id": "irs_samples_continue",
                "interaction_request_id": request.payload["interaction_request_id"],
                "response_status": "submitted",
                "confirmation_decision": "confirmed",
                "target_identity": request.payload["target_identity"],
                "state_snapshot_identity": request.payload["state_snapshot_identity"],
                "host_surface_identity": "phase9_test",
                "submitted_at": "2026-05-26T00:00:00Z",
            }
        )
    )

    import semantic_control_kernel.services.agent_tool_workflow_dispatch as dispatch

    monkeypatch.setattr(dispatch, "_database_creation_runtime", lambda state_paths: runtime)
    result = dispatch.continue_workflow_after_interaction(
        workflow_run_id="wr_sample_continue",
        workflow_tool="empty_database_default_taxonomy_custom_projections",
        state_paths=paths,
    )

    assert result is not None
    assert result.status == "ok"
    events = [event.to_dict() for event in ProgressEventStore(paths).list_progress_events("wr_sample_continue")]
    completed = [event["step_id"] for event in events if event["status"] == "step_completed"]
    assert "proj_analyze_samples" in completed
    assert "rel_activate_custom_release" in completed
    assert not any("already exists" in event["user_visible_summary"] for event in events)
