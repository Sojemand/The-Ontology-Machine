from __future__ import annotations

from pathlib import Path

from test_phase11_fakes import (
    FakeOrchestratorAdapter,
    confirmation_for,
    final_manifest_for,
    input_files,
    owner_output,
    owner_output_for_request,
    runtime_for,
    target_for,
)
from semantic_control_kernel.workflows.pipeline_run.run import pipeline_run


def test_pipeline_run_happy_path_publishes_final_manifest_after_correlation(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = pipeline_run(
        runtime=runtime_for(tmp_path),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_pipeline_happy",
    )

    assert execution.status == "completed"
    assert execution.artifacts["correlation_report"]["manifest_eligible"] is True
    assert Path(execution.artifacts["final_manifest_path"]).exists()
    assert execution.artifacts["final_manifest"]["pipeline_batch_id"].startswith("pbt_")


def test_pipeline_run_blocks_when_owner_output_omits_materialization_refs(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = pipeline_run(
        runtime=runtime_for(
            tmp_path,
            orchestrator_adapter=FakeOrchestratorAdapter(owner_output(), enrich_materialization_refs=False),
        ),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_missing_materialization_refs",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "materialization_provenance_missing"
    assert "final_manifest" not in execution.artifacts


def test_pipeline_run_blocks_when_owner_output_omits_owner_run_evidence(tmp_path) -> None:
    target = target_for(tmp_path)
    output = owner_output()
    del output["owner_run_refs"]

    execution = pipeline_run(
        runtime=runtime_for(tmp_path, orchestrator_adapter=FakeOrchestratorAdapter(output)),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_missing_owner_run_refs",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "partial_pipeline_run"
    assert any(item["code"] == "owner_run_evidence_missing" for item in execution.blocker.diagnostics)


def test_pipeline_run_blocks_when_input_file_disposition_is_missing(tmp_path) -> None:
    target = target_for(tmp_path)
    output = owner_output()
    output["input_file_dispositions"] = []

    execution = pipeline_run(
        runtime=runtime_for(tmp_path, orchestrator_adapter=FakeOrchestratorAdapter(output)),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_missing_input_disposition",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "partial_pipeline_run"
    assert any(item["code"] == "input_file_disposition_missing" for item in execution.blocker.diagnostics)
    assert "final_manifest" not in execution.artifacts


def test_pipeline_run_refuses_to_overwrite_existing_final_manifest(tmp_path) -> None:
    target = target_for(tmp_path)
    source_manifest = final_manifest_for(target)
    source_path = Path(target.artifact_root_path) / "Documents" / "logs" / "pipeline_batches" / source_manifest["pipeline_batch_id"] / "pipeline_batch_manifest.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_text = "existing immutable manifest\n"
    source_path.write_text(source_text, encoding="utf-8")
    state = {
        "owner_run_completed": True,
        "correlation_pending": True,
        "target_identity": target.target_identity,
        "pipeline_batch_id": source_manifest["pipeline_batch_id"],
        "owner_adapter_result": {
            "status": "ok",
            "kernel_function": "pipeline_run",
            "adapter_name": "phase11_fake",
            "adapter_call_id": "adapter_resume",
            "capability_status": "implemented_in_pipeline",
            "diagnostics": [],
            "output_refs": owner_output_for_request(
                {
                    "pipeline_batch_id": source_manifest["pipeline_batch_id"],
                    "semantic_release": target.semantic_release_manifest_ref(),
                    "active_projections": target.projection_manifest_refs(),
                    "input_files": input_files(),
                },
                output=owner_output(),
            ),
            "receipt_fields": {},
            "target_identity_proof": {},
        },
    }

    execution = pipeline_run(
        runtime=runtime_for(tmp_path),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_immutable_manifest",
        resume_state=state,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "partial_pipeline_run"
    assert source_path.read_text(encoding="utf-8") == source_text


def test_pipeline_run_count_mismatch_blocks_as_partial_pipeline_run(tmp_path) -> None:
    output = owner_output()
    output["database_record_counts"]["documents"] = 99
    target = target_for(tmp_path)
    execution = pipeline_run(
        runtime=runtime_for(tmp_path, orchestrator_adapter=FakeOrchestratorAdapter(output)),
        target=target,
        input_files=input_files(),
        confirmation=confirmation_for(target, "pipeline_run"),
        workflow_run_id="wf_count_mismatch",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "partial_pipeline_run"
    assert execution.blocker.recovery_state_class == "partial_pipeline_run"
    assert "final_manifest" not in execution.artifacts
