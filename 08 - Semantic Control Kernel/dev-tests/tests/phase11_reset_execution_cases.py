from __future__ import annotations

from pathlib import Path

from test_phase11_fakes import FakeCorpusAdapter, confirmation_for, final_manifest_for, runtime_for, target_for

from semantic_control_kernel.workflows.pipeline_run.reset import reset_database


def test_reset_database_requires_confirmation_receipt(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(tmp_path),
        target=target,
        confirmation=None,
        workflow_run_id="wf_reset_no_confirm",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "confirmation_missing"


def test_reset_database_accepts_kernel_confirmation_receipt_shape(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(tmp_path),
        target=target,
        confirmation={
            "schema_version": "kernel.confirmation_receipt.v1",
            "confirmation_receipt_id": "cfr_reset_001",
            "confirmation_request_id": "cir_reset_001",
            "confirmed_target_identity": target.target_identity,
            "confirmed_state_snapshot_identity": {"state_snapshot_id": target.state_snapshot_id},
            "user_decision": "confirmed",
            "confirmed_at": "2026-05-30T12:00:00Z",
            "explanation_hash": "hash",
            "host_surface_identity": "test",
        },
        workflow_run_id="wf_reset_receipt_shape",
        reresolved_target_identity=target.target_identity,
    )

    assert execution.status == "completed"
    assert execution.artifacts["database_reset_manifest"]["confirmation_receipt_ref"]["confirmation_receipt_id"] == "cfr_reset_001"


def test_reset_database_revalidates_target_identity_after_confirmation(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(tmp_path),
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_reset_changed_target",
        reresolved_target_identity={"database_path_hash": "changed"},
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "target_identity_changed"


def test_reset_database_preserves_active_release_and_supersedes_batch_refs(tmp_path) -> None:
    target = target_for(tmp_path)
    manifest = final_manifest_for(target)
    execution = reset_database(
        runtime=runtime_for(tmp_path),
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_reset_happy",
        batch_manifests=[manifest],
        reresolved_target_identity=target.target_identity,
    )

    reset_manifest = execution.artifacts["database_reset_manifest"]

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_active"
    assert reset_manifest["preserved_release_ref"]["release_fingerprint"] == target.release_fingerprint
    assert reset_manifest["superseded_batch_refs"] == [
        {
            "pipeline_batch_id": manifest["pipeline_batch_id"],
            "manifest_fingerprint": manifest["manifest_fingerprint"],
        }
    ]
    assert reset_manifest["empty_state_proven"] is True
    assert Path(execution.artifacts["database_reset_manifest_path"]).exists()
    assert execution.mirror_events[-1]["agent_explanation_guidance"]["response_mode"] == "emit_direct_message"
    assert execution.mirror_events[-1]["technical_detail_ref"]["workflow_completion"]["empty_state_proven"] is True


def test_reset_database_blocks_when_release_preservation_fails(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(tmp_path, corpus_adapter=FakeCorpusAdapter(preserve=False)),
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_reset_preserve_fail",
        reresolved_target_identity=target.target_identity,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "semantic_release_preservation_failed"


def test_reset_database_blocks_when_empty_state_is_not_proven(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(tmp_path, corpus_adapter=FakeCorpusAdapter(empty_state_proven=False)),
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_reset_empty_unproven",
        reresolved_target_identity=target.target_identity,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "semantic_release_preservation_failed"


def test_reset_database_blocks_when_owner_returns_different_target_identity(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = reset_database(
        runtime=runtime_for(
            tmp_path,
            corpus_adapter=FakeCorpusAdapter(target_identity_after={**target.target_identity, "database_path_hash": "sha256:changed"}),
        ),
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_reset_owner_identity_changed",
        reresolved_target_identity=target.target_identity,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "target_identity_changed"
