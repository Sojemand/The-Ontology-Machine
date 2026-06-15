from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from _phase9_fakes import FakeInteractionPort, FakeSemanticReleaseAdapter, load_default_release_fixture, runtime_for, target_for
from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation.routes import DatabaseCreationRuntime, run_database_creation_workflow


def test_complete_default_release_is_written_attached_and_activated(tmp_path: Path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter()
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_complete",
    )

    release_path = Path(target.semantic_release_path) / "releases" / "default.release.v1"
    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_active"
    assert (release_path / "release.json").is_file()
    assert "load_semantic_release" in semantic.calls
    assert "activate_semantic_release" in semantic.calls


def test_default_release_without_projection_blocks_before_attach_or_activate(tmp_path: Path) -> None:
    invalid = load_default_release_fixture()
    invalid["projection_refs"] = []
    semantic = FakeSemanticReleaseAdapter(default_release=invalid)
    target = target_for(tmp_path)

    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_invalid",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_incomplete"
    assert "load_semantic_release" not in semantic.calls
    assert "activate_semantic_release" not in semantic.calls


def test_default_release_without_taxonomy_identity_blocks_before_write(tmp_path: Path) -> None:
    invalid = load_default_release_fixture()
    invalid["taxonomy_ref"] = {"taxonomy_id": "default.taxonomy.v1"}
    semantic = FakeSemanticReleaseAdapter(default_release=invalid)
    target = target_for(tmp_path)

    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_invalid_taxonomy_identity",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_incomplete"
    assert "write_semantic_release" not in semantic.calls


def test_default_release_without_projection_identity_blocks_before_write(tmp_path: Path) -> None:
    invalid = load_default_release_fixture()
    invalid["projection_refs"] = [{"projection_fingerprint": "proj-default-fingerprint"}]
    semantic = FakeSemanticReleaseAdapter(default_release=invalid)
    target = target_for(tmp_path)

    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_invalid_projection_identity",
    )

    assert execution.status == "blocked"
    assert execution.blocker.blocker_code == "release_incomplete"
    assert "write_semantic_release" not in semantic.calls


@pytest.mark.skipif(
    os.environ.get("KERNEL_REAL_OWNER_SMOKE") != "1"
    or not (
        (Path(__file__).resolve().parents[3] / "00 - Orchestrator" / "runtime" / "python" / "python.exe").exists()
        and (Path(__file__).resolve().parents[3] / "04 - Normalizer" / "runtime" / "python" / "python.exe").exists()
        and (Path(__file__).resolve().parents[3] / "05 - Corpus Builder" / "runtime" / "python" / "python.exe").exists()
    ),
    reason="set KERNEL_REAL_OWNER_SMOKE=1 and provide owner runtimes for the real-owner default release smoke path",
)
def test_real_owner_default_release_path_reaches_semantic_release_active(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    target = target_for(tmp_path, name="Real Owner Artifact Tree", database_name="real_owner_kernel")
    runtime = DatabaseCreationRuntime(
        state_root=state_root,
        workspace_adapter=WorkspaceAdapter(state_root=state_root),
        corpus_adapter=CorpusAdapter(state_root=state_root),
        semantic_release_adapter=SemanticReleaseAdapter(state_root=state_root),
        interaction_port=FakeInteractionPort(target=target),
        blueprint_ref="default",
    )

    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_default_projections",
        runtime=runtime,
        workflow_run_id="wf_real_owner_default_ready",
    )

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_active"
    assert Path(target.database_path).is_file()
    assert Path(str(execution.artifacts["default_release_export_path"])).is_file()
    assert Path(str(execution.artifacts["default_release_path"])).is_file()
    assert "dc_activate_default_release" in execution.completed_step_ids


@pytest.mark.skipif(
    os.environ.get("KERNEL_REAL_OWNER_SMOKE") != "1"
    or not (
        (Path(__file__).resolve().parents[3] / "00 - Orchestrator" / "runtime" / "python" / "python.exe").exists()
        and (Path(__file__).resolve().parents[3] / "04 - Normalizer" / "runtime" / "python" / "python.exe").exists()
        and (Path(__file__).resolve().parents[3] / "05 - Corpus Builder" / "runtime" / "python" / "python.exe").exists()
    ),
    reason="set KERNEL_REAL_OWNER_SMOKE=1 and provide owner runtimes for the real-owner projectionless default release smoke path",
)
def test_real_owner_default_taxonomy_no_projections_reaches_semantic_release_incomplete(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    target = target_for(tmp_path, name="Real Owner Projectionless Tree", database_name="real_owner_projectionless")
    runtime = DatabaseCreationRuntime(
        state_root=state_root,
        workspace_adapter=WorkspaceAdapter(state_root=state_root),
        corpus_adapter=CorpusAdapter(state_root=state_root),
        semantic_release_adapter=SemanticReleaseAdapter(state_root=state_root),
        interaction_port=FakeInteractionPort(target=target),
        blueprint_ref="default",
    )

    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_no_projections",
        runtime=runtime,
        workflow_run_id="wf_real_owner_default_projectionless",
    )

    projectionless_path = Path(str(execution.artifacts["projectionless_release_state_path"]))
    projectionless_payload = json.loads(projectionless_path.read_text(encoding="utf-8"))
    marker_payload = json.loads((Path(target.semantic_release_path) / "incomplete_semantic_release.json").read_text(encoding="utf-8"))

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_incomplete"
    assert Path(target.database_path).is_file()
    assert projectionless_path.is_file()
    assert projectionless_payload["schema_version"] == "kernel.default_taxonomy_projectionless_release_state.v1"
    assert projectionless_payload["projectionless_release_ref"]["projection_refs"] == []
    assert projectionless_payload["remaining_projection_refs"] == []
    assert marker_payload["projectionless_release_state_ref"]["artifact_path"] == str(projectionless_path)
    assert marker_payload["projectionless_release_ref"]["projection_refs"] == []
    assert AttachStateStore(StatePaths.from_state_root(state_root)).get_attach_state_for_database(target.target_identity) is None
    assert "dc_remove_default_projections" in execution.completed_step_ids
    assert "dc_activate_default_release" not in execution.completed_step_ids
