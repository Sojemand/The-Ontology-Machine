from __future__ import annotations

from typing import Any

from .tool_handler_source_fit_compatibility import compatibility_review
from .tool_handler_source_fit_terms import (
    candidate_field_labels,
    document_concepts,
    flatten_text,
    limit_unique,
    normalized_terms,
    observed_field_evidence,
    source_sample_summary,
    unsupported,
)


_FIT_REIMPORT_FOLLOWUP_KERNEL_TOOLS = (
    "database_rebuild_from_artifacts",
    "reset_database",
    "manual_pipeline_run",
)
_FIT_REFINEMENT_FOLLOWUP_KERNEL_TOOLS = (
    "create_custom_taxonomy_path",
    "create_custom_projection_path",
    *_FIT_REIMPORT_FOLLOWUP_KERNEL_TOOLS,
)
_FIT_ROUTING_FOLLOWUP_KERNEL_TOOLS = (
    "create_custom_projection_path",
    "create_custom_taxonomy_path",
    "manual_pipeline_run",
)


def taxonomy_coverage_review(release: dict[str, Any], sample: dict[str, Any], projection_matches: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
    concepts = document_concepts(sample)
    release_terms = normalized_terms([*release.get("known_terms", []), *flatten_text(release.get("projections"))])
    field_evidence = observed_field_evidence(concepts)
    unsupported_fields = unsupported(field_evidence, release_terms, limit=12)
    unsupported_topics = unsupported([*concepts["headings"], *concepts["candidate_markers"]], release_terms, limit=12)
    delta_type = coverage_delta_type(release, projection_matches, unsupported_fields, unsupported_topics)
    compatibility = compatibility_review(delta_type)
    candidate_fields = candidate_field_labels(unsupported_fields, field_evidence)
    candidate_markers = limit_unique([*unsupported_topics, *concepts["candidate_markers"]], limit=16)
    return {
        "source_sample_summary": source_sample_summary(sample, concepts),
        "taxonomy_coverage": coverage_payload(release_terms, projection_matches, concepts, delta_type, candidate_fields, candidate_markers, release, sample),
        "working_release_refinement_request": refinement_request(arguments, sample, release, delta_type, candidate_fields, candidate_markers),
        "compatibility_review": compatibility,
        "refinement_advice": refinement_advice(delta_type, compatibility),
        "safe_next_kernel_tools": refinement_safe_next_kernel_tools(delta_type),
        "user_message_de": coverage_user_message(delta_type, candidate_fields, candidate_markers, compatibility),
    }


def coverage_payload(release_terms: set[str], matches: list[dict[str, Any]], concepts: dict[str, list[str]], delta_type: str, fields: list[str], markers: list[str], release: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "checked": True,
        "basis": "active semantic release plus local source-document sample inspection",
        "delta_type": delta_type,
        "visible_document_concepts": concepts,
        "observed_content_evidence": {
            "field_like_or_heading_phrases": [*concepts.get("field_like_phrases", []), *concepts.get("headings", [])],
            "routing_or_topic_markers": concepts.get("candidate_markers", []),
            "ignored_technical_hints": concepts.get("ignored_technical_hints", []),
        },
        "currently_supported_terms": sorted(release_terms)[:80],
        "candidate_projection_matches": matches,
        "missing_or_too_coarse_fields": fields,
        "missing_or_too_coarse_routing_markers": markers,
        "requires_agent_field_proposal": bool(fields),
        "warnings": coverage_warnings(release, sample, delta_type),
    }


def refinement_request(arguments: dict[str, Any], sample: dict[str, Any], release: dict[str, Any], delta_type: str, fields: list[str], markers: list[str]) -> dict[str, Any]:
    return {
        "artifact_folder": str(arguments.get("artifact_folder") or ""),
        "goal": refinement_goal(delta_type),
        "must_keep": must_keep_release_text(release),
        "noise_tolerance": "medium",
        "candidate_field_labels": fields,
        "candidate_routing_markers": markers,
        "source_document_path": str(arguments.get("source_document_path") or sample.get("source_document_path") or ""),
        "sample_label": str(arguments.get("sample_label") or sample.get("sample_label") or ""),
        "requires_human_review": True,
    }


def coverage_delta_type(release: dict[str, Any], projection_matches: list[dict[str, Any]], unsupported_fields: list[str], unsupported_topics: list[str]) -> str:
    if not release.get("projection_ids"):
        return "active_release_missing_or_unreported"
    if unsupported_fields:
        return "new_taxonomy_fields_likely"
    if unsupported_topics and not projection_matches:
        return "projection_or_routing_gap_likely"
    return "projection_guidance_may_need_refinement" if unsupported_topics else "no_structural_gap_detected"


def coverage_warnings(release: dict[str, Any], sample: dict[str, Any], delta_type: str) -> list[str]:
    warnings = fit_warnings(release, sample)
    if delta_type == "new_taxonomy_fields_likely":
        warnings.append("candidate fields are not an apply decision; review and revision classification are required")
    if delta_type == "active_release_missing_or_unreported":
        warnings.append("active release did not expose enough projection/taxonomy detail for a reliable coverage check")
    return warnings


def refinement_goal(delta_type: str) -> str:
    if delta_type == "new_taxonomy_fields_likely":
        return "Improve the active archive rules so fields visible in the new source document are represented without losing existing archive intent."
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement"}:
        return "Improve the active archive routing/profile guidance so this new source document is recognized by the right rules."
    return "Review whether the active archive rules need any small refinement for this source document."


def must_keep_release_text(release: dict[str, Any]) -> str:
    release_id = str(release.get("release_id") or "active release")
    projections = ", ".join(str(item) for item in release.get("projection_ids") or []) or "existing projections"
    master = str(release.get("master_taxonomy_release_id") or "current master taxonomy line")
    return f"Keep existing intent of {release_id}, projections {projections}, and do not silently change master line {master}."


def refinement_advice(delta_type: str, compatibility: dict[str, Any]) -> dict[str, Any]:
    why = "The document contains field-like concepts that are not clearly represented by the active release; review a working-release field proposal next."
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement"}:
        why = "The active projection/routing guidance may be too narrow for this document; review projection guidance next."
    if delta_type == "no_structural_gap_detected":
        why = "No clear coverage gap was detected, but a review workflow can still document that decision."
    return {
        "recommended_first_kernel_tool": recommended_refinement_kernel_tool(delta_type),
        "safe_next_kernel_tools": refinement_safe_next_kernel_tools(delta_type),
        "why": why,
        "do_not_use": ["stage_debug_single_document", "optimizer.classify_document"],
        "compatibility_warning_de": compatibility["user_message_de"],
    }


def coverage_user_message(delta_type: str, fields: list[str], markers: list[str], compatibility: dict[str, Any]) -> str:
    if delta_type == "new_taxonomy_fields_likely":
        return f"Ja: Das neue Dokument zeigt wahrscheinlich Inhalte, die die aktive Feldsammlung zu grob oder gar nicht abdeckt. Kandidaten: {', '.join(fields[:5]) or 'keine kompakten Feldnamen extrahiert'}. " + compatibility["user_message_de"]
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement"}:
        return f"Die Taxonomie wirkt nicht zwingend falsch, aber Profilwahl oder Erkennungsworte koennten zu eng sein. Hinweise: {', '.join(markers[:5]) or 'keine kompakten Marker extrahiert'}. " + compatibility["user_message_de"]
    if delta_type == "active_release_missing_or_unreported":
        return "Die aktive Regelversion meldet zu wenig Taxonomie-/Profilinformationen. Ich kann nur eine vorsichtige Review-Schiene empfehlen."
    return "Ich sehe in diesem Sample keine klare strukturelle Taxonomie-Luecke. Eine spaetere Testnormalisierung kann das noch genauer belegen."


def fit_warnings(release: dict[str, Any], sample: dict[str, Any]) -> list[str]:
    warnings = []
    if not release.get("projection_ids"):
        warnings.append("active release did not report projection ids")
    if not sample:
        warnings.append("source sample inspection returned no sample payload")
    return warnings


def refinement_safe_next_kernel_tools(delta_type: str) -> list[str]:
    if delta_type == "active_release_missing_or_unreported":
        return ["kernel_status", "create_custom_taxonomy_path", "create_custom_projection_path"]
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement", "no_structural_gap_detected"}:
        return list(_FIT_ROUTING_FOLLOWUP_KERNEL_TOOLS)
    return list(_FIT_REFINEMENT_FOLLOWUP_KERNEL_TOOLS)


def recommended_refinement_kernel_tool(delta_type: str) -> str | None:
    if delta_type == "active_release_missing_or_unreported":
        return "kernel_status"
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement", "no_structural_gap_detected"}:
        return "create_custom_projection_path"
    return "create_custom_taxonomy_path"


__all__ = [name for name in globals() if not name.startswith("__")]
