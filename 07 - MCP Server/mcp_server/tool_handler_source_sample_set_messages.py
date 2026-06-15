from __future__ import annotations

from collections import Counter
from typing import Any

from .tool_handler_source_fit_review import compatibility_review
from .tool_handler_source_fit_terms import limit_unique


def compatibility_payload(delta_type: str, sample_count: int) -> dict[str, Any]:
    source_type = "new_taxonomy_fields_likely" if "taxonomy" in delta_type else "projection_or_routing_gap_likely" if "routing" in delta_type else "no_structural_gap_detected"
    base = compatibility_review(source_type)
    base["sample_set_guard"] = "Do not make one-sample-only signals mandatory fields."
    base["sample_count"] = sample_count
    return base


def refinement_request(arguments: dict[str, Any], release: dict[str, Any], aggregate: dict[str, Any], delta_type: str) -> dict[str, Any]:
    recurring = [item["label"] for item in aggregate["taxonomy_coverage"]["recurring_field_candidates"]]
    subgroup = [item["label"] for item in aggregate["taxonomy_coverage"]["subgroup_field_candidates"]]
    one_off = [item["label"] for item in aggregate["taxonomy_coverage"]["one_off_field_candidates"]]
    return {
        "artifact_folder": str(arguments.get("artifact_folder") or ""),
        "goal": _goal(delta_type, recurring, subgroup),
        "must_keep": _must_keep(release, recurring, subgroup, one_off),
        "noise_tolerance": "medium",
        "candidate_field_labels": limit_unique([*recurring, *subgroup], limit=16),
        "optional_or_low_confidence_field_labels": limit_unique(one_off, limit=16),
        "source_document_paths": aggregate["sample_set"]["source_document_paths"],
        "sample_set_review_policy": "Prefer recurring or subgroup evidence; do not overfit the release to a single sample.",
        "requires_human_review": True,
    }


def sample_set_warnings(sample_count: int, clusters: Counter[str], field_groups: dict[str, list[dict[str, Any]]]) -> list[str]:
    warnings = []
    if sample_count == 1:
        warnings.append("Only one sample was reviewed; use the single-document workflow or add more samples before making broad taxonomy changes.")
    if len(clusters) > 1:
        warnings.append("The sample set is heterogeneous; recurring fields should stay core, subgroup fields may need profile-specific guidance.")
    if field_groups["one_off"]:
        warnings.append("One-off field candidates are reported as optional review notes, not mandatory new archive fields.")
    return warnings


def user_message(delta_type: str, aggregate: dict[str, Any], compatibility: dict[str, Any]) -> str:
    coverage = aggregate["taxonomy_coverage"]
    if delta_type == "sample_set_taxonomy_fields_likely":
        labels = [item["label"] for item in [*coverage["recurring_field_candidates"], *coverage["subgroup_field_candidates"]]][:6]
        return f"Ja: Ueber mehrere Samples hinweg gibt es wiederkehrende Inhalte, die die aktuelle Feldsammlung wahrscheinlich zu grob abdeckt: {', '.join(labels)}. " + compatibility["user_message_de"]
    if delta_type == "sample_set_projection_or_routing_gap_likely":
        return "Die Felder wirken nicht zwingend falsch, aber Profilwahl oder Erkennungsworte sind fuer diese Dokumentgruppe wahrscheinlich zu eng. " + compatibility["user_message_de"]
    if delta_type == "one_off_candidates_need_more_evidence":
        return "Es gibt einzelne Kandidaten, aber sie tauchen nur in jeweils einem Sample auf. Ich wuerde daraus noch keine Pflichtfelder machen, sondern sie als optionale Hinweise pruefen."
    return "Im Sample-Set sehe ich keine klare strukturelle Taxonomie-Luecke."


def _goal(delta_type: str, recurring: list[str], subgroup: list[str]) -> str:
    if "taxonomy" in delta_type:
        return "Improve the active archive rules so recurring content patterns across the representative document set are represented without losing existing archive intent: " + ", ".join([*recurring, *subgroup])
    if "routing" in delta_type:
        return "Sharpen document profile/routing guidance for this representative document set without changing fields unnecessarily."
    return "Review whether this representative document set needs archive rule refinement."


def _must_keep(release: dict[str, Any], recurring: list[str], subgroup: list[str], one_off: list[str]) -> str:
    projections = ", ".join(str(item) for item in release.get("projection_ids") or []) or "existing projections"
    candidates = ", ".join([*recurring, *subgroup]) or "none"
    optional = ", ".join(one_off[:6]) or "none"
    return f"Keep all existing fields, document types, projections ({projections}), and archive intent from the active release. Recurring sample-set candidates: {candidates}. One-off candidates are review notes only: {optional}."


__all__ = [name for name in globals() if not name.startswith("__")]
