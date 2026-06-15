from __future__ import annotations

from pathlib import Path

from test_phase11_fakes import FakeBatchAdapter, FakeOrchestratorAdapter
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.workflows.pipeline_run.run import PipelineRunRuntime
from phase11_manual_pipeline_agent_support import AgentManualCorpusAdapter, _pending, _state_paths, _submit

def test_agent_manual_pipeline_flow_can_restore_error_cases_before_input_confirmation(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    db_path = root / "Corpus" / "Fantasy.db"
    input_dir = root / "Input"
    error_original = root / "Error Cases" / "Validator" / "Documents" / "originals" / "story.pdf"
    db_path.parent.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    (root / "Documents").mkdir()
    (root / "Semantic Release").mkdir()
    error_original.parent.mkdir(parents=True)
    (root / "Error Cases" / "Validator" / "Documents" / "logs").mkdir(parents=True)
    (root / "Error Cases" / "Validator" / "Documents" / "logs" / "story.pdf.error_manifest.json").write_text("{}", encoding="utf-8")
    (root / "Error Cases" / "Validator" / "Documents" / "raw_extracts").mkdir(parents=True)
    (root / "Error Cases" / "Validator" / "Documents" / "raw_extracts" / "story.pdf.p001.of001.raw.json").write_text("{}", encoding="utf-8")
    db_path.write_text("active", encoding="utf-8")
    error_original.write_text("recover me", encoding="utf-8")
    batch_adapter = FakeBatchAdapter()

    class RestoringOrchestratorAdapter(FakeOrchestratorAdapter):
        def reset_error_cases(self, request_payload=None):
            result = super().reset_error_cases(request_payload)
            restored = input_dir / "story.pdf"
            restored.write_text(error_original.read_text(encoding="utf-8"), encoding="utf-8")
            error_original.unlink()
            return result

    orchestrator_adapter = RestoringOrchestratorAdapter()

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
    workflow_run_id = started["workflow_run_id"]
    choose_request = _pending(paths, workflow_run_id)
    _submit(paths, choose_request, "irs_restore_choose", path_value=str(root))

    restore_request = _pending(paths, workflow_run_id)
    assert restore_request.payload["interaction_function"] == "user_confirmation"
    assert restore_request.payload["user_visible_title"] == "Restore Error Cases"
    assert "Input is empty" in restore_request.payload["user_visible_summary"]
    assert restore_request.payload["prefilled_values"]["error_case_file_count"] == 1

    restored = _submit(paths, restore_request, "irs_restore_error_cases", confirmation_decision="confirmed")
    assert restored["continued_workflow_result"]["effect"] == "workflow_started"
    assert orchestrator_adapter.reset_error_cases_calls

    input_confirmation = _pending(paths, workflow_run_id)
    assert input_confirmation.payload["interaction_function"] == "select_sample_files"
    assert input_confirmation.payload["prefilled_values"]["input_file_count"] == 1

    confirmed = _submit(paths, input_confirmation, "irs_restore_confirm_input", confirmation_decision="confirmed")
    assert confirmed["continued_workflow_result"]["effect"] == "workflow_completed"
    assert confirmed["continued_workflow_result"]["final_state"] == "semantic_release_active"
    assert orchestrator_adapter.calls[-1]["input_files"][0]["input_relative_path"] == "Input/story.pdf"

def test_agent_manual_pipeline_offers_error_case_restore_even_when_input_has_files(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    db_path = root / "Corpus" / "Fantasy.db"
    input_dir = root / "Input"
    active_input = input_dir / "new_story.txt"
    error_original = root / "Error Cases" / "Validator" / "Documents" / "originals" / "old_story.pdf"
    db_path.parent.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    (root / "Documents").mkdir()
    (root / "Semantic Release").mkdir()
    error_original.parent.mkdir(parents=True)
    db_path.write_text("active", encoding="utf-8")
    active_input.write_text("new work", encoding="utf-8")
    error_original.write_text("retry work", encoding="utf-8")
    orchestrator_adapter = FakeOrchestratorAdapter()

    def runtime_factory(state_paths: StatePaths) -> PipelineRunRuntime:
        return PipelineRunRuntime(
            state_root=state_paths.state_root,
            batch_adapter=FakeBatchAdapter(),
            orchestrator_adapter=orchestrator_adapter,
            corpus_adapter=AgentManualCorpusAdapter(),
        )

    original_reset = orchestrator_adapter.reset_error_cases

    def reset_error_cases(request_payload=None):
        result = original_reset(request_payload)
        restored = input_dir / "old_story.pdf"
        restored.write_text(error_original.read_text(encoding="utf-8"), encoding="utf-8")
        error_original.unlink()
        return result

    orchestrator_adapter.reset_error_cases = reset_error_cases
    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._pipeline_runtime",
        runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("manual_pipeline_run", state_paths=paths).to_dict()
    workflow_run_id = started["workflow_run_id"]
    choose_request = _pending(paths, workflow_run_id)
    _submit(paths, choose_request, "irs_mixed_choose", path_value=str(root))

    restore_request = _pending(paths, workflow_run_id)
    assert restore_request.payload["interaction_function"] == "user_confirmation"
    assert restore_request.payload["user_visible_title"] == "Restore Error Cases"
    assert "Input is empty" not in restore_request.payload["user_visible_summary"]
    assert "Existing Input file(s) will be kept" in restore_request.payload["user_visible_summary"]

    _submit(paths, restore_request, "irs_mixed_restore", confirmation_decision="confirmed")
    input_confirmation = _pending(paths, workflow_run_id)
    assert input_confirmation.payload["interaction_function"] == "select_sample_files"
    assert input_confirmation.payload["prefilled_values"]["input_file_count"] == 2

    confirmed = _submit(paths, input_confirmation, "irs_mixed_confirm", confirmation_decision="confirmed")
    assert confirmed["continued_workflow_result"]["effect"] == "workflow_completed"
    assert sorted(item["input_relative_path"] for item in orchestrator_adapter.calls[-1]["input_files"]) == [
        "Input/new_story.txt",
        "Input/old_story.pdf",
    ]

def test_agent_manual_pipeline_decline_error_case_restore_continues_with_existing_input(tmp_path: Path, monkeypatch) -> None:
    paths = _state_paths(tmp_path)
    root = tmp_path / "Artifact Tree"
    db_path = root / "Corpus" / "Fantasy.db"
    input_dir = root / "Input"
    active_input = input_dir / "new_story.txt"
    error_original = root / "Error Cases" / "Validator" / "Documents" / "originals" / "old_story.pdf"
    db_path.parent.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    (root / "Documents").mkdir()
    (root / "Semantic Release").mkdir()
    error_original.parent.mkdir(parents=True)
    db_path.write_text("active", encoding="utf-8")
    active_input.write_text("new work", encoding="utf-8")
    error_original.write_text("retry work", encoding="utf-8")
    orchestrator_adapter = FakeOrchestratorAdapter()

    def runtime_factory(state_paths: StatePaths) -> PipelineRunRuntime:
        return PipelineRunRuntime(
            state_root=state_paths.state_root,
            batch_adapter=FakeBatchAdapter(),
            orchestrator_adapter=orchestrator_adapter,
            corpus_adapter=AgentManualCorpusAdapter(),
        )

    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._pipeline_runtime",
        runtime_factory,
    )

    started = dispatch_permanent_workflow_tool("manual_pipeline_run", state_paths=paths).to_dict()
    workflow_run_id = started["workflow_run_id"]
    choose_request = _pending(paths, workflow_run_id)
    _submit(paths, choose_request, "irs_decline_choose", path_value=str(root))

    restore_request = _pending(paths, workflow_run_id)
    assert restore_request.payload["user_visible_title"] == "Restore Error Cases"

    declined = _submit(paths, restore_request, "irs_decline_restore", confirmation_decision="declined")
    assert declined["continued_workflow_result"]["effect"] == "workflow_started"

    input_confirmation = _pending(paths, workflow_run_id)
    assert input_confirmation.payload["interaction_function"] == "select_sample_files"
    assert input_confirmation.payload["prefilled_values"]["input_file_count"] == 1
    assert orchestrator_adapter.reset_error_cases_calls == []
