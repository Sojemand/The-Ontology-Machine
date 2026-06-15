from __future__ import annotations

from pathlib import Path

from phase11_reset_support import (
    AgentResetCorpusAdapter,
    pending_interaction,
    state_paths_for,
    submit_interaction,
)

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime


def test_agent_reset_flow_collects_target_confirms_and_runs_reset(tmp_path: Path, monkeypatch) -> None:
    paths = state_paths_for(tmp_path)
    root = tmp_path / "Artifact Tree"
    db_path = root / "Corpus" / "Fantasy.db"
    db_path.parent.mkdir(parents=True)
    (root / "Input").mkdir()
    (root / "Documents").mkdir()
    (root / "Semantic Release").mkdir()
    db_path.write_text("filled", encoding="utf-8")
    corpus_adapter = AgentResetCorpusAdapter()

    def runtime_factory(state_paths: StatePaths) -> PipelineRunRuntime:
        return PipelineRunRuntime(
            state_root=state_paths.state_root,
            batch_adapter=object(),
            orchestrator_adapter=object(),
            corpus_adapter=corpus_adapter,
        )

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._pipeline_runtime",
        runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("reset_database", state_paths=paths).to_dict()
    assert started["status"] == "ok"
    workflow_run_id = started["workflow_run_id"]
    choose_request = pending_interaction(paths, workflow_run_id)
    assert choose_request.payload["interaction_function"] == "choose_artifact_root_folder"

    submit_interaction(paths, choose_request, "irs_reset_choose", path_value=str(root))
    name_request = pending_interaction(paths, workflow_run_id)
    assert name_request.payload["interaction_function"] == "name_database"

    named = submit_interaction(paths, name_request, "irs_reset_name", text_value="Fantasy.db")
    assert named["continued_workflow_result"]["effect"] == "workflow_started"
    confirmation_request = pending_interaction(paths, workflow_run_id)
    assert confirmation_request.payload["interaction_function"] == "user_confirmation"
    assert confirmation_request.payload["risk_class"] == "destructive"
    assert confirmation_request.payload["state_snapshot_identity"]["state_snapshot_id"] == "snapshot_reset_agent"

    confirmed = submit_interaction(
        paths,
        confirmation_request,
        "irs_reset_confirm",
        confirmation_decision="confirmed",
    )

    assert confirmed["continued_workflow_result"]["effect"] == "workflow_completed"
    assert confirmed["continued_workflow_result"]["final_state"] == "semantic_release_active"
    mirror_event = confirmed["continued_workflow_result"]["mirror_event"]
    assert mirror_event["agent_explanation_guidance"]["response_mode"] == "emit_direct_message"
    assert mirror_event["technical_detail_ref"]["kind"] == "database_reset_workflow_completion"
    assert corpus_adapter.reset_payloads[-1]["database_path"] == str(db_path.resolve(strict=False))
