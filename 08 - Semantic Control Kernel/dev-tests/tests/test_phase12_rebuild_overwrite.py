from __future__ import annotations

from phase12_merge_entry_support import FakeEmbeddingAdapter, create_artifact_tree, seed_rebuild_release
from test_phase12_rebuild_workflow import rebuild_runtime

from semantic_control_kernel.workflows.rebuild.entry import database_rebuild_from_artifacts


def test_rebuild_existing_target_requires_overwrite_receipt(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    target = root / "Corpus" / "existing.db"
    target.write_text("old", encoding="utf-8")
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="existing.db",
        workflow_run_id="wf_overwrite_missing",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "confirmation_missing"
    assert execution.progress_events[-1]["schema_version"] == "kernel.progress_event.v1"
    assert execution.artifacts["overwrite_required_for"]["loaded_release_fingerprint"] == "sha256:tree_release"


def test_rebuild_overwrite_receipt_scope_allows_rebuild_after_revalidation(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    target = root / "Corpus" / "existing.db"
    target.write_text("old", encoding="utf-8")
    receipt = {
        "status": "confirmed",
        "artifact_root": str(root),
        "target_database_path": str(target),
        "loaded_release_fingerprint": "sha256:tree_release",
        "workflow_run_id": "wf_overwrite_ok",
        "confirmation_receipt_id": "receipt_overwrite",
    }
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path, embedding=FakeEmbeddingAdapter()),
        artifact_root=root,
        target_database_name="existing.db",
        workflow_run_id="wf_overwrite_ok",
        overwrite_receipt=receipt,
    )

    assert execution.status == "completed"
    assert execution.artifacts["overwrite_receipt_id"] == "receipt_overwrite"


def test_stale_overwrite_receipt_is_rejected(tmp_path) -> None:
    root = tmp_path / "Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    target = root / "Corpus" / "existing.db"
    target.write_text("old", encoding="utf-8")
    receipt = {
        "status": "confirmed",
        "artifact_root": str(root),
        "target_database_path": str(target),
        "loaded_release_fingerprint": "sha256:other",
        "workflow_run_id": "wf_overwrite_stale",
    }
    execution = database_rebuild_from_artifacts(
        runtime=rebuild_runtime(tmp_path),
        artifact_root=root,
        target_database_name="existing.db",
        workflow_run_id="wf_overwrite_stale",
        overwrite_receipt=receipt,
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "confirmation_missing"
