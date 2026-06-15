from __future__ import annotations

from edit_suite.ui import review_result_view


def test_review_result_sections_render_readable_review_payload() -> None:
    sections = review_result_view.sections_from_response(
        {
            "headline": "Data-informed review ready",
            "summary_lines": ["Sample: case-a", "Empfohlene Projection: housing.default.v1"],
            "applied_changes": [{"action": "extend_projection", "target": "housing.default.v1", "reason": "known code added"}],
            "changed_source_files": ["master.text.de.yaml"],
            "current_release_fingerprint": "old",
            "candidate_release_fingerprint": "new",
            "release_fingerprint_changed": True,
            "review_payload": {
                "input_summary": {"sample_label": "case-a", "structured_sample_path": "C:/tmp/case_a.structured.json"},
                "release_summary": {"release_id": "semantic_release.default", "candidate_fingerprint": "abc123"},
                "projection_suggestions": [
                    {
                        "projection_id": "housing.default.v1",
                        "label": "Housing",
                        "score": 4,
                        "recommended": True,
                        "action": "reuse_with_review",
                        "reason": "fallback selection",
                    }
                ],
                "master_term_suggestions": [{"section_id": "field_codes", "term_id": "tenant_share_heating_cost", "label": "tenant_share_heating_cost", "suggestion_type": "new", "reason": "missing in master"}],
                "routing_review": {"selected_projection_id": "housing.default.v1", "selected_reason": "fallback", "candidate_rankings": [{"projection_id": "housing.default.v1", "score": 4, "signals": ["marker"]}]},
                "document_comparison": {"original": {"status": "missing"}, "structured": {"status": "loaded"}, "normalized": {"status": "loaded"}},
                "information_balance": {"kept": ["issuer"], "condensed": ["document_type: report -> utility_cost_statement"], "lost": ["kostenuebersicht"]},
                "warnings": ["Routing-Lexika liefern fuer dieses Sample kaum belastbare Treffer."],
                "next_steps": ["Projection pruefen", "Master aktualisieren"],
            },
        }
    )

    labels = [label for label, _body in sections]
    assert labels == [
        "Summary",
        "Input Summary",
        "Release Summary",
        "Projection Suggestions",
        "Master Term Suggestions",
        "Applied Source Changes",
        "Preview Delta",
        "Routing Review",
        "Document Comparison",
        "Behalten / Verdichtet / Verloren",
        "Warnings",
        "Next Steps",
    ]
    assert "[recommended] housing.default.v1" in dict(sections)["Projection Suggestions"]
    assert "extend_projection | housing.default.v1" in dict(sections)["Applied Source Changes"]
    assert "Current fingerprint: old" in dict(sections)["Preview Delta"]
    assert "Behalten: issuer" in dict(sections)["Behalten / Verdichtet / Verloren"]
