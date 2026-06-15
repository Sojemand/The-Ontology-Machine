from __future__ import annotations

import pytest

from _phase9_fakes import runtime_for, target_for
from semantic_control_kernel.repository.paths import StatePaths
import semantic_control_kernel.workflows.database_creation.routes as creation_routes
from semantic_control_kernel.workflows.database_creation.resume import (
    assert_resume_context_fresh,
    build_resume_context,
    resume_inputs_for_tool,
    resume_context_is_fresh,
)
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


def test_no_semantic_release_persists_resume_state(tmp_path) -> None:
    target = target_for(tmp_path)
    execution = run_database_creation_workflow(
        "empty_database_no_semantic_release",
        runtime=runtime_for(tmp_path, target=target),
        workflow_run_id="wf_no_release_resume",
    )
    paths = StatePaths.from_state_root(tmp_path / "state")

    assert execution.status == "completed"
    assert execution.final_state == "no_semantic_release"
    assert execution.resume_context is not None
    assert "empty_database_default_taxonomy_default_projections" in execution.resume_context.allowed_continuation_workflow_tools
    assert "create_custom_taxonomy_path" in execution.resume_context.allowed_continuation_workflow_tools
    assert "create_custom_projection_path" not in execution.resume_context.allowed_continuation_workflow_tools
    assert (paths.resume_dir / "wf_no_release_resume.resume.json").is_file()


def test_staged_taxonomy_resume_rejects_changed_component_fingerprint(tmp_path) -> None:
    target = target_for(tmp_path)
    staged = {
        "component_kind": "taxonomy",
        "fingerprint": "tax1",
        "stage_id": "tax_stage",
        "artifact_ref": {"artifact_path": "tax"},
        "component_identity": {"taxonomy_id": "tax"},
    }
    context = build_resume_context(
        workflow_run_id="wf_resume",
        workflow_tool="empty_database_custom_taxonomy_no_projections",
        last_completed_step_id="tax_stage_custom_taxonomy",
        next_step_id="proj_require_taxonomy",
        target=target,
        state_snapshot_id="snap",
        staged_component_refs=[staged],
        allowed_continuation_workflow_tools=["create_custom_projection_path"],
    )

    assert resume_context_is_fresh(context, current_target_identity=target.target_identity, current_staged_component_refs=[staged])
    changed = {**staged, "fingerprint": "tax2"}
    assert not resume_context_is_fresh(context, current_target_identity=target.target_identity, current_staged_component_refs=[changed])
    superseded = {**staged, "stage_id": "tax_stage_2"}
    assert not resume_context_is_fresh(context, current_target_identity=target.target_identity, current_staged_component_refs=[superseded])


def test_staged_taxonomy_resume_rehydrates_update_state_for_projection_authoring(tmp_path) -> None:
    target = target_for(tmp_path)
    update_state = {
        "schema_version": "kernel.create_taxonomy_update_state.input.v1",
        "taxonomy_core": {
            "domains": [{"code": "finance"}],
            "document_types": [{"code": "invoice"}],
            "categories": [{"code": "finance"}],
            "subcategories": [{"code": "other"}],
            "field_codes": [{"code": "amount_due"}],
            "row_types": [{"code": "line_item"}],
            "cell_codes": [{"code": "description"}],
            "fallback_codes": {"field_code": "other"},
        },
        "taxonomy_text": {"locale": "en"},
        "semantic_binding": {"field_codes": [{"code": "amount_due", "promotion_slot": "amount_due"}]},
    }
    staged = {
        "component_kind": "taxonomy",
        "fingerprint": "tax1",
        "stage_id": "tax_stage",
        "artifact_ref": {"artifact_path": "tax"},
        "component_identity": {"taxonomy_id": "tax", "taxonomy_fingerprint": "tax1", "runtime_locale": "en"},
        "source_analysis_refs": [update_state],
    }
    context = build_resume_context(
        workflow_run_id="wf_resume",
        workflow_tool="empty_database_custom_taxonomy_no_projections",
        last_completed_step_id="tax_stage_custom_taxonomy",
        next_step_id="proj_require_taxonomy",
        target=target,
        state_snapshot_id="snap",
        final_state="semantic_release_incomplete",
        staged_component_refs=[staged],
        allowed_continuation_workflow_tools=["create_custom_projection_path"],
    )

    _, artifacts, _, _ = resume_inputs_for_tool("create_custom_projection_path", context)

    assert artifacts["taxonomy_ref"]["taxonomy_core"] == update_state["taxonomy_core"]
    assert artifacts["taxonomy_ref"]["field_codes"] == [{"code": "amount_due"}]
    assert artifacts["taxonomy_ref"]["fallback_codes"] == ["other"]


def test_staged_projection_only_resume_rejects_target_identity_change(tmp_path) -> None:
    target = target_for(tmp_path, name="Resume A")
    other = target_for(tmp_path, name="Resume B")
    context = build_resume_context(
        workflow_run_id="wf_projection_resume",
        workflow_tool="create_custom_projection_path",
        last_completed_step_id="proj_stage_custom_projection",
        next_step_id="rel_create_custom_release",
        target=target,
        state_snapshot_id="snap",
        staged_component_refs=[{"component_kind": "projections", "fingerprint": "proj1"}],
        allowed_continuation_workflow_tools=["create_custom_projection_path"],
    )

    assert not resume_context_is_fresh(context, current_target_identity=other.target_identity, current_staged_component_refs=[{"component_kind": "projections", "fingerprint": "proj1"}])
    try:
        assert_resume_context_fresh(context, current_target_identity=other.target_identity, current_staged_component_refs=[])
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale resume context was accepted")


def test_resume_persistence_failure_does_not_claim_resumable_completion(tmp_path, monkeypatch) -> None:
    target = target_for(tmp_path)

    def fail_persist(*args, **kwargs):
        raise OSError("resume store unavailable")

    monkeypatch.setattr(creation_routes, "persist_resume_context", fail_persist)

    with pytest.raises(OSError, match="resume store unavailable"):
        run_database_creation_workflow(
            "empty_database_no_semantic_release",
            runtime=runtime_for(tmp_path, target=target),
            workflow_run_id="wf_resume_store_failure",
        )
