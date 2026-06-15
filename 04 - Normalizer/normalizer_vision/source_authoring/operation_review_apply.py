"""Review/apply source-authoring operations."""
from __future__ import annotations

from typing import Any

from . import adapter
from .bootstrap_plan import build_bootstrap_plan
from .impact_preview import describe_package_delta
from .refine_plan import build_refine_plan
from .response import build_response


def preview_impact(project_root) -> dict[str, object]:
    context = adapter.load_context(project_root)
    impact = describe_package_delta(project_root, context["package"], materialization_version=context["materialization_version"])
    return build_response(
        "preview_impact",
        headline="Impact preview ready",
        summary_lines=[
            f"Changed source files: {len(impact['changed_source_files'])}",
            f"Current release fingerprint: {impact['current_release_fingerprint']}",
            f"Candidate release fingerprint: {impact['candidate_release_fingerprint']}",
        ],
        changed_assets=impact["changed_source_files"],
        changed_source_files=impact["changed_source_files"],
        current_release_fingerprint=impact["current_release_fingerprint"],
        candidate_release_fingerprint=impact["candidate_release_fingerprint"],
        release_fingerprint_changed=impact["release_fingerprint_changed"],
        references_existing_codes=context["package"]["release"]["projection_ids"],
        compile_effect="Compiling validates the saved source package and prepares semantic-release export input in memory.",
        prompt_effect="Locale and routing text changes can alter projection guidance and prompt context.",
        corpus_effect="A changed release fingerprint will require downstream export and activation for corpus visibility.",
    )


def bootstrap_release_package(project_root, payload: dict[str, Any]) -> dict[str, object]:
    plan = build_bootstrap_plan(project_root, payload)
    saved = adapter.save_context(project_root, plan["candidate_package"])
    return _applied_response("bootstrap_release_package", "Bootstrap draft saved", saved, plan, ["goal", "must_keep", "noise_tolerance"])


def refine_release_package(project_root, payload: dict[str, Any]) -> dict[str, object]:
    plan = build_refine_plan(project_root, payload)
    saved = adapter.save_context(project_root, plan["candidate_package"])
    return _applied_response("refine_release_package", "Data-informed draft saved", saved, plan, ["structured_sample_path", "expected_normalized_path"])


def _applied_response(action: str, headline: str, saved: dict[str, Any], plan: dict[str, Any], required_fields: list[str]) -> dict[str, object]:
    impact = plan["impact"]
    review_payload = plan["review_payload"]
    return build_response(
        action,
        headline=headline,
        summary_lines=[
            f"Release: {saved['release']['release_id']}",
            f"Selected projection: {review_payload['routing_review']['selected_projection_id']}",
            f"Applied source changes: {len(plan['applied_changes'])}",
            f"Changed source files: {len(impact['changed_source_files'])}",
        ],
        review_payload=review_payload,
        applied_changes=plan["applied_changes"],
        changed_assets=impact["changed_source_files"],
        changed_source_files=impact["changed_source_files"],
        current_release_fingerprint=impact["current_release_fingerprint"],
        candidate_release_fingerprint=impact["candidate_release_fingerprint"],
        release_fingerprint_changed=impact["release_fingerprint_changed"],
        references_existing_codes=plan["references"],
        required_fields=required_fields,
        compile_effect="Only source files plus the aligned release recipe were updated; compile/export now reads directly from that saved source state.",
        prompt_effect="Saved authoring changes now affect later review and compile input, but not runtime outputs yet.",
        corpus_effect="No corpus-visible change exists until compile, export, and activation run.",
    )
