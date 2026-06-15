from __future__ import annotations

from phase12_merge_entry_support import FakeCorpusAdapter, FakeEmbeddingAdapter, FakeSemanticReleaseAdapter, create_artifact_tree, ok_result, seed_rebuild_release

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.rebuild.entry import RebuildWorkflowRuntime, database_rebuild_from_artifacts


def rebuild_runtime(tmp_path, *, corpus=None, semantic=None, embedding=None):
    return RebuildWorkflowRuntime(
        state_root=tmp_path / "state",
        corpus_adapter=corpus or FakeCorpusAdapter(),
        semantic_release_adapter=semantic or FakeSemanticReleaseAdapter(),
        embedding_adapter=embedding or FakeEmbeddingAdapter(),
    )


def test_rebuild_loads_release_uses_exact_target_runs_builder_and_activates(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_rebuild",
        embedding_provider_configured=True,
    )

    assert execution.status == "completed"
    assert execution.target_database_path.endswith("Corpus\\rebuilt.db") or execution.target_database_path.endswith("Corpus/rebuilt.db")
    assert "corpus_builder_load_semantic_release" in execution.operation_log
    assert "run_corpus_builder" in execution.operation_log
    assert "activate_semantic_release" in execution.operation_log
    assert execution.artifacts["rebuild_manifest"]["loaded_release_fingerprint"] == "sha256:tree_release"
    assert all(event["schema_version"] == "kernel.progress_event.v1" for event in execution.progress_events)
    attach_state = AttachStateStore(StatePaths.from_state_root(tmp_path / "state")).get_attach_state_for_database({"database_path": execution.target_database_path})
    assert attach_state is not None
    assert attach_state.to_dict()["release_id"] == "tree.release"


def test_rebuild_persists_embedding_progress_events_with_visible_summary(tmp_path) -> None:
    class CountingEmbeddingAdapter(FakeEmbeddingAdapter):
        def create_embeddings(self, request_payload=None):
            self.calls.append("create_embeddings")
            return ok_result("create_embeddings", {"embedding_count": 15, "embedding_result": "completed"})

    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, embedding=CountingEmbeddingAdapter()),
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_rebuild_progress",
        embedding_provider_configured=True,
    )

    events = [event.to_dict() for event in ProgressEventStore(StatePaths.from_state_root(tmp_path / "state")).list_progress_events("wf_rebuild_progress")]
    embedding_events = [event for event in events if event["step_id"] == "creating_embeddings"]
    assert execution.status == "completed"
    assert [event["status"] for event in embedding_events] == ["step_started", "step_completed"]
    assert embedding_events[0]["user_visible_summary"] == "Creating embedding vectors for the rebuilt database. This can take a while."
    assert embedding_events[1]["user_visible_summary"] == "Embedding vectors created for 15 records."
    assert [event["sequence_index"] for event in events] == list(range(1, len(events) + 1))


def test_rebuild_accepts_owner_fingerprint_alias_for_loaded_release(tmp_path) -> None:
    class FingerprintOnlySemanticReleaseAdapter(FakeSemanticReleaseAdapter):
        def load_semantic_release_from_artifact_tree(self, request_payload=None):
            self.calls.append("load_semantic_release_from_artifact_tree")
            release_path = seed_rebuild_release(root)
            return ok_result(
                "corpus_builder_load_semantic_release",
                {
                    "fingerprint": "sha256:tree_release",
                    "release_id": "tree.release",
                    "release_path": str(release_path / "release.json"),
                    "release_version": "2.0.0",
                },
            )

    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)

    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, semantic=FingerprintOnlySemanticReleaseAdapter()),
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_rebuild_fingerprint_alias",
        embedding_provider_configured=True,
    )

    assert execution.status == "completed"
    assert execution.artifacts["loaded_release"]["loaded_release_fingerprint"] == "sha256:tree_release"


def test_rebuild_blocks_when_primitive_cannot_prove_exact_target(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, corpus=FakeCorpusAdapter(insufficient_rebuild=True)),
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_rebuild_bad_target",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "rebuild_primitive_insufficient"


def test_rebuild_blocks_when_primitive_omits_loaded_release_identity(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, corpus=FakeCorpusAdapter(omit_release_identity=True)),
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_rebuild_missing_release_identity",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "rebuild_primitive_insufficient"


def test_rebuild_invalid_target_name_returns_typed_blocker(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="../escape",
        workflow_run_id="wf_rebuild_invalid_target",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "invalid_target_path"


def test_rebuild_missing_semantic_release_folder_blocks(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    (root / "Corpus").mkdir(parents=True)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="missing_release",
        workflow_run_id="wf_missing_release",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_missing"
    assert execution.blocker.recovery_state_class == "semantic_release_incomplete_staged"


def test_rebuild_release_folder_without_release_package_blocks(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="empty_release_folder",
        workflow_run_id="wf_incomplete_release_folder",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_incomplete"
