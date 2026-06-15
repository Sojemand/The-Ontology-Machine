from __future__ import annotations

import shutil

from _phase9_fakes import runtime_for, target_for
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_existing_binding_conflict_blocks_cleanly_instead_of_crashing(tmp_path) -> None:
    target = target_for(tmp_path, name="Artifact Tree Conflict", database_name="kernel_conflict")
    first_runtime = runtime_for(tmp_path, target=target)
    first_execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=first_runtime,
        workflow_run_id="wr_binding_seed",
    )
    assert first_execution.status == "completed"

    artifact_root = target.artifact_root_path
    if shutil.which("cmd") is not None:  # keep Windows file cleanup simple and deterministic
        shutil.rmtree(artifact_root)
    else:
        shutil.rmtree(artifact_root)

    second_runtime = runtime_for(tmp_path, target=target)
    second_execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=second_runtime,
        workflow_run_id="wr_binding_conflict",
    )

    assert second_execution.status == "blocked"
    assert second_execution.blocker is not None
    assert second_execution.blocker.blocker_code == "binding_conflict"
    assert second_execution.blocked_step_id == "dc_create_empty_database"
