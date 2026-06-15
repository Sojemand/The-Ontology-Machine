from __future__ import annotations

from test_phase11_fakes import FakeBatchAdapter, FakeOrchestratorAdapter, confirmation_for, input_files, owner_error, runtime_for, target_for

from semantic_control_kernel.workflows.pipeline_run.manual import manual_pipeline_run
from semantic_control_kernel.workflows.pipeline_run.run import pipeline_run


def test_pipeline_run_requires_active_release_before_owner_mutation(tmp_path) -> None:
    target = target_for(tmp_path, semantic_release_state="no_semantic_release")
    orchestrator = FakeOrchestratorAdapter()
    execution = pipeline_run(
        runtime=runtime_for(tmp_path, orchestrator_adapter=orchestrator),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_release_missing",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_missing"
    assert orchestrator.calls == []


def test_pipeline_run_requires_exact_binding_proof(tmp_path) -> None:
    target = target_for(tmp_path, binding=False)
    execution = pipeline_run(
        runtime=runtime_for(tmp_path),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_binding_missing",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "binding_conflict"


def test_manual_pipeline_run_requires_input_confirmation(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = manual_pipeline_run(
        runtime=runtime_for(tmp_path),
        target=target,
        input_files=input_files(),
        workflow_run_id="wf_confirm_missing",
        confirmation=None,
    )

    assert execution.status == "blocked"
    assert execution.workflow_tool == "manual_pipeline_run"
    assert execution.blocker.blocker_code == "input_missing"
    assert execution.blocker.function_or_route == "manual_pipeline_run"


def test_missing_batch_owner_capability_blocks_before_orchestrator_mutation(tmp_path) -> None:
    target = target_for(tmp_path)
    batch = FakeBatchAdapter(missing_methods=["create_batch_manifest"])
    orchestrator = FakeOrchestratorAdapter()
    execution = pipeline_run(
        runtime=runtime_for(tmp_path, batch_adapter=batch, orchestrator_adapter=orchestrator),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_missing_batch_capability",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "pipeline_capability_missing"
    assert execution.blocker.recovery_state_class == "support_only_unrecoverable"
    assert orchestrator.calls == []
    assert "pending_manifest" in execution.artifacts


def test_pipeline_run_surfaces_owner_error_diagnostic_summary(tmp_path) -> None:
    target = target_for(tmp_path)

    class FailingOrchestratorAdapter(FakeOrchestratorAdapter):
        def run_pipeline(self, request_payload=None, *, progress_callback=None):
            self.calls.append(dict(request_payload or {}))
            if progress_callback is not None:
                progress_callback()
            return owner_error(
                "pipeline_run",
                [{"code": "owner_response_error", "summary": "Healthcheck failed: Interpreter provider timeout."}],
            )

    execution = pipeline_run(
        runtime=runtime_for(tmp_path, orchestrator_adapter=FailingOrchestratorAdapter()),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_owner_error_summary",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "partial_pipeline_run"
    assert "owner_error: Healthcheck failed: Interpreter provider timeout." in execution.blocker.user_visible_summary
