from __future__ import annotations

from edit_suite.ui import preview_result_view
from edit_suite.ui.action_workflow_text import details_text


def test_preview_result_sections_render_fingerprint_and_asset_delta() -> None:
    sections = preview_result_view.sections_from_value(
        {
            "result": {
                "headline": "Impact preview ready",
                "summary_lines": ["Changed source files: 1"],
                "changed_source_files": ["master.text.de.yaml"],
                "current_release_fingerprint": "old",
                "candidate_release_fingerprint": "new",
                "release_fingerprint_changed": True,
                "compile_effect": "Compile would validate source files and materialize release-ready payloads.",
                "prompt_effect": "Prompt context would change.",
                "corpus_effect": "Corpus export would be required.",
            }
        }
    )

    mapping = dict(sections)
    assert mapping["Changed Source Files"] == "master.text.de.yaml"
    assert "Current: old" in mapping["Release Fingerprint Delta"]
    assert "Candidate: new" in mapping["Release Fingerprint Delta"]
    assert "Changed: True" in mapping["Release Fingerprint Delta"]
    assert "Compile: Compile would validate source files and materialize release-ready payloads." in mapping["Effects"]


def test_preview_result_sections_render_source_preview_summaries() -> None:
    sections = preview_result_view.sections_from_value(
        {
            "current_summary": {"projection_count": 1, "release_id": "rel.v1"},
            "draft_summary": {"projection_count": 2, "release_id": "rel.v2"},
            "diff": "--- current\n+++ draft",
        }
    )

    mapping = dict(sections)
    assert "projection_count: 1" in mapping["Current Summary"]
    assert "projection_count: 2" in mapping["Draft Summary"]
    assert mapping["Diff"] == "--- current\n+++ draft"


def test_action_workflow_details_text_formats_stage_effects_and_risks() -> None:
    text = details_text(
        {
            "workflow_stage": "compile",
            "workflow_order": 50,
            "compile_effect": "Materializes release-ready payloads in memory.",
            "prompt_effect": "Prompt context updates after compile.",
            "corpus_effect": "No corpus-visible change until export.",
            "validation_risks": ["Compile should follow validation.", "Only saved files are compiled."],
        }
    )

    assert "Workflow: 50 - compile" in text
    assert "Compile: Materializes release-ready payloads in memory." in text
    assert "Prompt: Prompt context updates after compile." in text
    assert "Corpus: No corpus-visible change until export." in text
    assert "Validation risks: Compile should follow validation. | Only saved files are compiled." in text
