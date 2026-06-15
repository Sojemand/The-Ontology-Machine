from __future__ import annotations

from phase12_merge_entry_support import FakeEmbeddingAdapter, create_artifact_tree, ok_result, seed_rebuild_release
from test_phase12_rebuild_workflow import rebuild_runtime

from semantic_control_kernel.workflows.rebuild.entry import database_rebuild_from_artifacts


def test_configured_embeddings_are_created(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    embedding = FakeEmbeddingAdapter()
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, embedding=embedding),
        artifact_root=root,
        target_database_name="embeddings",
        workflow_run_id="wf_embeddings",
        embedding_provider_configured=True,
    )

    assert execution.status == "completed"
    assert embedding.calls == ["create_embeddings"]
    assert execution.artifacts["rebuild_manifest"]["embedding_result"] == "created"


def test_orchestrator_completed_embedding_result_is_recorded_as_created(tmp_path) -> None:
    class CompletedEmbeddingAdapter(FakeEmbeddingAdapter):
        def create_embeddings(self, request_payload=None):
            self.calls.append("create_embeddings")
            return ok_result("create_embeddings", {"embedding_result": "completed"})

    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    embedding = CompletedEmbeddingAdapter()
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, embedding=embedding),
        artifact_root=root,
        target_database_name="completed_embeddings",
        workflow_run_id="wf_completed_embeddings",
        embedding_provider_configured=True,
    )

    assert execution.status == "completed"
    assert embedding.calls == ["create_embeddings"]
    assert execution.artifacts["rebuild_manifest"]["embedding_result"] == "created"


def test_optional_unconfigured_embeddings_are_skipped_and_recorded(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="skip_embeddings",
        workflow_run_id="wf_embedding_skip",
    )

    assert execution.status == "completed"
    assert execution.artifacts["rebuild_manifest"]["embedding_result"] == "skipped_unconfigured"


def test_required_embedding_provider_missing_blocks(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="required_embeddings",
        workflow_run_id="wf_embedding_required",
        embedding_policy="required",
        embedding_provider_configured=False,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "embedding_provider_unavailable"


def test_provider_failure_keeps_rebuilt_database_visible_and_blocks(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, embedding=FakeEmbeddingAdapter(fail=True)),
        artifact_root=root,
        target_database_name="provider_failure",
        workflow_run_id="wf_embedding_failure",
        embedding_provider_configured=True,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "embedding_provider_failure"
    assert execution.artifacts["rebuilt_database_visible"].endswith("provider_failure.db")
