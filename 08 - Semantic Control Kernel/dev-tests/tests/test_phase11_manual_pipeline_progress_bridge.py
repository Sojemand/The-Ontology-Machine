from __future__ import annotations

import json
from pathlib import Path

from test_phase11_fakes import FakeBatchAdapter, FakeOrchestratorAdapter, confirmation_for, input_files, target_for
from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.services.agent_workflow_manual_pipeline_runner import sync_manual_pipeline_workflow_run
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.workflows.pipeline_run.progress_bridge import OrchestratorSnapshotProgressBridge
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime, pipeline_run
from phase11_manual_pipeline_agent_support import AgentManualCorpusAdapter, _state_paths

def test_orchestrator_snapshot_errors_are_completed_progress_when_run_finishes(tmp_path: Path) -> None:
    paths = _state_paths(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps({"is_running": False, "total": 2, "completed": 2, "success": 1, "errors": 1}),
        encoding="utf-8",
    )

    OrchestratorSnapshotProgressBridge(
        paths,
        workflow_run_id="wr_progress",
        workflow_tool="manual_pipeline_run",
        snapshot_path=snapshot_path,
    ).poll()

    events = ProgressEventStore(paths).list_progress_events("wr_progress")
    payload = events[-1].to_dict()
    assert payload["status"] == "completed"
    assert "1 errors" in payload["user_visible_summary"]

def test_orchestrator_snapshot_progress_carries_all_stage_rows(tmp_path: Path) -> None:
    paths = _state_paths(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "is_running": True,
                "total": 1,
                "completed": 0,
                "success": 0,
                "errors": 1,
                "needs_review": 0,
                "error_cases_folder": {
                    "path": str(tmp_path / "Artifact Tree" / "Error Cases"),
                    "exists": True,
                    "file_count": 2,
                    "latest_files": ["failed_page_13.json", "failed_page_12.json"],
                },
                "stage_statuses": {
                    "Intake": {"status": "Fertig", "detail": "1 input file"},
                    "Interpreter": {
                        "status": "Verarbeite...",
                        "detail": "large.pdf",
                        "progress_current": 12,
                        "progress_total": 59,
                        "progress_label": "Requests",
                    },
                    "Validator": {"status": "Bereit", "detail": ""},
                },
            }
        ),
        encoding="utf-8",
    )

    OrchestratorSnapshotProgressBridge(
        paths,
        workflow_run_id="wr_progress_stages",
        workflow_tool="manual_pipeline_run",
        snapshot_path=snapshot_path,
    ).poll()

    payload = ProgressEventStore(paths).list_progress_events("wr_progress_stages")[-1].to_dict()
    assert payload["status"] == "step_started"
    assert "stage=Interpreter: Verarbeite... 12/59 Requests" in payload["current_state_summary"]
    assert "Error Cases folder has 2 source file(s)" in payload["user_visible_summary"]
    stage_ref = payload["artifact_refs"][0]
    assert stage_ref["kind"] == "orchestrator_stage_statuses"
    assert [stage["name"] for stage in stage_ref["stages"]] == ["Intake", "Interpreter", "Validator", "Error Cases"]
    assert stage_ref["stages"][1]["progress_total"] == 59
    assert stage_ref["stages"][-1]["detail"] == "1 error(s) | 2 source file(s) in folder | failed_page_13.json, failed_page_12.json"

def test_pipeline_run_finalizes_when_snapshot_progress_sequence_races(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    workflow_run_id = "wr_progress_race"
    target = target_for(tmp_path, workflow_run_id=workflow_run_id)
    WorkflowRunStore(paths).create_run(
        "manual_pipeline_run",
        target.target_identity,
        "phase11_test",
        workflow_run_id=workflow_run_id,
    )
    ProgressEventStore(paths).append_progress_event(
        ProgressEvent.from_dict(
            {
                "schema_version": ProgressEvent.SCHEMA_VERSION,
                "workflow_run_id": workflow_run_id,
                "workflow_tool": "manual_pipeline_run",
                "step_id": "existing_progress",
                "step_label": "existing_progress",
                "event_type": "pipeline_step",
                "status": "step_started",
                "sequence_index": 1,
                "user_visible_summary": "Existing progress event.",
                "current_state_summary": "existing",
                "timestamp": "2026-06-02T19:00:00Z",
            }
        )
    )

    original_next_sequence_index = ProgressEventStore.next_sequence_index
    sequence_calls = {"count": 0}

    def racing_next_sequence_index(self, run_id: str) -> int:
        if run_id == workflow_run_id and sequence_calls["count"] == 0:
            sequence_calls["count"] += 1
            return 1
        return original_next_sequence_index(self, run_id)

    monkeypatch.setattr(ProgressEventStore, "next_sequence_index", racing_next_sequence_index)

    class SnapshotRaceOrchestrator(FakeOrchestratorAdapter):
        def run_pipeline(self, request_payload=None, *, progress_callback=None):
            payload = dict(request_payload or {})
            snapshot_path = Path(str(payload["snapshot_path"]))
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(
                json.dumps(
                    {
                        "is_running": False,
                        "total": 1,
                        "completed": 1,
                        "success": 1,
                        "errors": 0,
                        "needs_review": 0,
                        "current_file": "source.pdf",
                        "stage_statuses": {
                            "Interpreter": {
                                "status": "Done",
                                "detail": "Page 2/2",
                                "progress_current": 2,
                                "progress_total": 2,
                                "progress_label": "Pages",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            if progress_callback is not None:
                progress_callback()
            return super().run_pipeline(payload, progress_callback=None)

    execution = pipeline_run(
        runtime=PipelineRunRuntime(
            state_root=paths.state_root,
            batch_adapter=FakeBatchAdapter(),
            orchestrator_adapter=SnapshotRaceOrchestrator(),
            corpus_adapter=AgentManualCorpusAdapter(),
        ),
        target=target,
        input_files=input_files(),
        workflow_run_id=workflow_run_id,
        confirmation=confirmation_for(target),
        workflow_tool="manual_pipeline_run",
    )
    sync_manual_pipeline_workflow_run(execution.to_dict(), state_paths=paths)

    assert execution.status == "completed"
    assert execution.mirror_events[-1]["event_type"] == "workflow_completed"
    assert WorkflowRunStore(paths).list_active_runs() == []
    assert WorkflowRunStore(paths).get_run(workflow_run_id).status == "completed"
    events = [event.to_dict() for event in ProgressEventStore(paths).list_progress_events(workflow_run_id)]
    assert [event["sequence_index"] for event in events] == [1, 2]
    assert events[-1]["status"] == "completed"
