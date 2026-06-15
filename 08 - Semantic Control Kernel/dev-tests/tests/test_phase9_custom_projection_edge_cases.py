from __future__ import annotations

from pathlib import Path

from _phase9_fakes import FakeLLMPort, FakeSemanticReleaseAdapter, load_default_release_fixture, runtime_for, target_for
from semantic_control_kernel.adapters.semantic_release import _projection_refs_from_payload
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_staged_projection_set_identity_expands_to_all_projection_refs() -> None:
    projection_refs = [
        {"projection_id": "finance.receipts.v1", "projection_fingerprint": "fp_receipts"},
        {"projection_id": "finance.payments.v1", "projection_fingerprint": "fp_payments"},
    ]
    payload = {
        "staged_projection_ref": {
            "component_identity": {
                "projection_ids": ["finance.receipts.v1", "finance.payments.v1"],
                "projection_refs": projection_refs,
            }
        }
    }

    assert _projection_refs_from_payload(payload) == projection_refs


def test_custom_projection_path_rejects_missing_sample_file_without_llm_call(tmp_path) -> None:
    target = target_for(tmp_path)
    llm = FakeLLMPort()
    semantic = FakeSemanticReleaseAdapter()
    missing_sample = {"sample_id": "ghost", "path": str(Path(target.input_path) / "ghost.json")}

    execution = run_database_creation_workflow(
        "create_custom_projection_path",
        runtime=runtime_for(
            tmp_path,
            target=target,
            semantic_adapter=semantic,
            llm_port=llm,
            projection_samples=[missing_sample],
            taxonomy_ref=load_default_release_fixture()["taxonomy_ref"],
        ),
        workflow_run_id="wf_projection_missing_sample_file",
        initial_final_state="semantic_release_active",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "input_missing"
    assert llm.calls == []
    assert semantic.calls == []
