from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.state_machine.spec_disagreement import detect_workflow_spec_disagreements


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
WORKFLOW_SPECS = {
    "05_database_creation_workflows.md": PIPELINE_ROOT / "Semantic Kernel SPEC" / "05_database_creation_workflows.md",
    "06_database_modification_workflows.md": PIPELINE_ROOT / "Semantic Kernel SPEC" / "06_database_modification_workflows.md",
    "07_pipeline_merge_rebuild_workflows.md": PIPELINE_ROOT / "Semantic Kernel SPEC" / "07_pipeline_merge_rebuild_workflows.md",
}


def test_current_workflow_specs_do_not_publish_explicit_state_claims_that_conflict_with_spec_02() -> None:
    disagreements = detect_workflow_spec_disagreements(WORKFLOW_SPECS)

    assert [item.to_dict() for item in disagreements] == []


def test_detector_reports_structured_disagreement_when_workflow_claim_conflicts() -> None:
    workflow_text = """
pipeline_run
    - Required State: no_semantic_release
    - Post-State: semantic_release_active
    - Confirmation: input_presence_confirmation
"""

    disagreements = detect_workflow_spec_disagreements({"synthetic.md": workflow_text})

    assert len(disagreements) == 1
    report = disagreements[0].to_dict()
    assert report["workflow_spec"] == "synthetic.md"
    assert report["workflow_route"] == "pipeline_run"
    assert report["state_table_rule_id"] == "tr_015"
    assert report["required_correction"].startswith("Update workflow checklist text")
