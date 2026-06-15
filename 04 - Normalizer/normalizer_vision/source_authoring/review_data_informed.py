"""Data-informed review helpers for source-backed release authoring."""
from __future__ import annotations

from typing import Any

from .refine_plan import build_refine_plan
from .response import build_response


def review_data_informed_release(project_root, payload: dict[str, Any]) -> dict[str, object]:
    plan = build_refine_plan(project_root, payload)
    impact = plan["impact"]
    review_payload = plan["review_payload"]
    return build_response(
        "review_data_informed_release",
        headline="Data-informed review ready",
        summary_lines=[
            f"Sample: {review_payload['input_summary']['sample_label']}",
            f"Empfohlene Projection: {review_payload['routing_review']['selected_projection_id']}",
            f"Geplante Source-Aenderungen: {len(plan['applied_changes'])}",
            f"Neue Master-Begriffe: {len([item for item in review_payload['master_term_suggestions'] if item['suggestion_type'] == 'new'])}",
        ],
        review_payload=review_payload,
        applied_changes=plan["applied_changes"],
        changed_assets=impact["changed_source_files"],
        changed_source_files=impact["changed_source_files"],
        current_release_fingerprint=impact["current_release_fingerprint"],
        candidate_release_fingerprint=impact["candidate_release_fingerprint"],
        release_fingerprint_changed=impact["release_fingerprint_changed"],
        references_existing_codes=plan["references"],
        required_fields=["structured_sample_path", "expected_normalized_path"],
        validation_risks=["data_informed_review_is_advisory_only"],
        prompt_effect="Data-informed review shows the same planned source changes and routing implications that the mutating refine action would apply.",
    )
