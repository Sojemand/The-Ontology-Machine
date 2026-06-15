"""Bootstrap review helpers for source-backed release authoring."""
from __future__ import annotations

from typing import Any

from .bootstrap_plan import build_bootstrap_plan
from .response import build_response


def review_bootstrap_release(project_root, payload: dict[str, Any]) -> dict[str, object]:
    plan = build_bootstrap_plan(project_root, payload)
    impact = plan["impact"]
    review_payload = plan["review_payload"]
    return build_response(
        "review_bootstrap_release",
        headline="Bootstrap review ready",
        summary_lines=[
            f"Release: {review_payload['release_summary']['release_id']}",
            f"Candidate release fingerprint: {impact['candidate_release_fingerprint']}",
            f"Empfohlene Projection: {review_payload['routing_review']['selected_projection_id']}",
            f"Geplante Source-Aenderungen: {len(plan['applied_changes'])}",
        ],
        review_payload=review_payload,
        applied_changes=plan["applied_changes"],
        changed_assets=impact["changed_source_files"],
        changed_source_files=impact["changed_source_files"],
        current_release_fingerprint=impact["current_release_fingerprint"],
        candidate_release_fingerprint=impact["candidate_release_fingerprint"],
        release_fingerprint_changed=impact["release_fingerprint_changed"],
        references_existing_codes=plan["references"],
        allowed_values=["low", "medium", "high"],
        required_fields=["goal", "must_keep", "noise_tolerance"],
        validation_risks=["bootstrap_review_is_advisory_only"],
        prompt_effect="Bootstrap review shows the same planned source changes and routing shifts that the mutating bootstrap action would apply.",
    )
