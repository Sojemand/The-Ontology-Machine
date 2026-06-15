from __future__ import annotations

import json
from pathlib import Path

from _phase9_fakes import FakeSemanticReleaseAdapter, load_default_release_fixture, runtime_for, target_for
from semantic_control_kernel.domain.state_machine.evaluator import StateMachineEvaluator
from semantic_control_kernel.domain.state_machine.models import TransitionInputRefs
from semantic_control_kernel.domain.state_machine.transition_table import get_transition_rule
from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_default_taxonomy_without_projection_is_incomplete_and_resumable(tmp_path: Path) -> None:
    target = target_for(tmp_path)
    semantic = FakeSemanticReleaseAdapter()
    execution = run_database_creation_workflow(
        "empty_database_default_taxonomy_no_projections",
        runtime=runtime_for(tmp_path, target=target, semantic_adapter=semantic),
        workflow_run_id="wf_default_no_projection",
    )

    marker = Path(target.semantic_release_path) / "incomplete_semantic_release.json"
    state_paths = StatePaths.from_state_root(tmp_path / "state")
    projectionless_state = Path(str(execution.artifacts["projectionless_release_state_path"]))
    projectionless_payload = json.loads(projectionless_state.read_text(encoding="utf-8"))
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    default_release = load_default_release_fixture()

    assert execution.status == "completed"
    assert execution.final_state == "semantic_release_incomplete"
    assert "activate_semantic_release" not in semantic.calls
    assert execution.resume_context is not None
    assert execution.resume_context.allowed_continuation_workflow_tools == ("create_custom_projection_path",)
    remove_payload = semantic.last_payloads["remove_taxonomy_or_projection"][0]
    assert remove_payload["release_ref"]["schema_version"] == "kernel.default_semantic_release_ref.v1"
    assert remove_payload["semantic_release_path"] == target.semantic_release_path
    assert remove_payload["corpus_db_path"] == target.database_path
    assert marker.is_file()
    assert "create_custom_projection_path" in marker.read_text(encoding="utf-8")
    assert projectionless_state.is_file()
    assert projectionless_payload["schema_version"] == "kernel.default_taxonomy_projectionless_release_state.v1"
    assert projectionless_payload["taxonomy_ref"]["taxonomy_id"] == default_release["taxonomy_ref"]["taxonomy_id"]
    assert projectionless_payload["projectionless_release_ref"]["projection_refs"] == []
    assert projectionless_payload["remaining_projection_refs"] == []
    assert len(projectionless_payload["removed_projection_refs"]) == len(default_release["projection_refs"])
    assert marker_payload["projectionless_release_state_ref"]["artifact_path"] == str(projectionless_state)
    assert marker_payload["projectionless_release_ref"]["projection_refs"] == []
    assert AttachStateStore(state_paths).get_attach_state_for_database(target.target_identity) is None
    assert list(state_paths.attach_states_history_dir.rglob("*.json"))


def test_pipeline_run_and_activation_block_for_incomplete_release(tmp_path: Path) -> None:
    target = target_for(tmp_path)
    state = {
        "schema_version": "kernel.active_database_state.v1",
        "state_snapshot_id": "snap",
        "artifact_tree": {"exists": True, "target_identity": target.target_identity},
        "active_database": {"database_exists": True, "target_identity": target.target_identity},
        "database_emptiness": "empty",
        "semantic_release_state": "semantic_release_incomplete",
        "blocking_reasons": [],
        "active_lock_refs": [],
        "evidence_refs": [],
    }
    pipeline_rule = get_transition_rule("pipeline_run")
    activation_rule = get_transition_rule("activate_semantic_release")

    pipeline = StateMachineEvaluator().evaluate("pipeline_run", state, TransitionInputRefs.for_rule(pipeline_rule))
    activation = StateMachineEvaluator().evaluate("activate_semantic_release", state, TransitionInputRefs.for_rule(activation_rule))

    assert pipeline.status == "blocked"
    assert activation.status == "blocked"
