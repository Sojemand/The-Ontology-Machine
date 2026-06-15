from __future__ import annotations

from pathlib import Path

from test_phase11_fakes import FakeBatchAdapter, FakeOrchestratorAdapter
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime
from phase11_manual_pipeline_agent_support import AgentManualCorpusAdapter, _pending, _state_paths, _submit

def test_agent_manual_pipeline_flow_collects_artifact_confirms_input_and_runs(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    db_path = root / "Corpus" / "Fantasy.db"
    input_path = root / "Input" / "story.txt"
    db_path.parent.mkdir(parents=True)
    input_path.parent.mkdir(parents=True)
    (root / "Documents").mkdir()
    (root / "Semantic Release").mkdir()
    db_path.write_text("active", encoding="utf-8")
    input_path.write_text("once upon a pipeline", encoding="utf-8")
    batch_adapter = FakeBatchAdapter()
    orchestrator_adapter = FakeOrchestratorAdapter()

    def runtime_factory(state_paths: StatePaths) -> PipelineRunRuntime:
        return PipelineRunRuntime(
            state_root=state_paths.state_root,
            batch_adapter=batch_adapter,
            orchestrator_adapter=orchestrator_adapter,
            corpus_adapter=AgentManualCorpusAdapter(),
        )

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._pipeline_runtime",
        runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("manual_pipeline_run", state_paths=paths).to_dict()
    assert started["status"] == "ok"
    workflow_run_id = started["workflow_run_id"]
    choose_request = _pending(paths, workflow_run_id)
    assert choose_request.payload["interaction_function"] == "choose_artifact_root_folder"

    after_choose = _submit(paths, choose_request, "irs_manual_choose", path_value=str(root))
    assert after_choose["continued_workflow_result"]["effect"] == "workflow_started"
    confirmation_request = _pending(paths, workflow_run_id)
    assert confirmation_request.payload["interaction_function"] == "select_sample_files"
    assert confirmation_request.payload["prefilled_values"]["input_file_count"] == 1

    confirmed = _submit(
        paths,
        confirmation_request,
        "irs_manual_confirm",
        confirmation_decision="confirmed",
    )

    assert confirmed["continued_workflow_result"]["effect"] == "workflow_completed"
    assert confirmed["continued_workflow_result"]["final_state"] == "semantic_release_active"
    assert orchestrator_adapter.calls[-1]["ui_state"]["selected_corpus_db_path"] == str(db_path.resolve(strict=False))
    assert orchestrator_adapter.calls[-1]["ui_state"]["input_folder"] == str((root / "Input").resolve(strict=False))
    snapshot_path = Path(orchestrator_adapter.calls[-1]["snapshot_path"]).resolve(strict=False)
    assert snapshot_path.relative_to(root.resolve(strict=False))
    assert orchestrator_adapter.calls[-1]["input_files"][0]["input_relative_path"] == "Input/story.txt"
    mirror_event = confirmed["continued_workflow_result"]["mirror_event"]
    assert mirror_event["agent_explanation_guidance"]["response_mode"] == "explain_now"
    assert mirror_event["technical_detail_ref"]["kind"] == "manual_pipeline_run_workflow_completion"
    assert (root / "Documents" / "logs" / "pipeline_batches").exists()
