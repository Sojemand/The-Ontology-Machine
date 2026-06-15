"""Deterministic repair rules for sample-analysis seed outputs."""

from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.validation.llm.common import _STATUS_ALIASES
from semantic_control_kernel.validation.llm.context import LLMValidationContext


def repair_sample_analysis_seed(payload: dict[str, Any], context: LLMValidationContext) -> None:
    sample_set = payload.setdefault("sample_set", {})
    if isinstance(sample_set, dict) and context.expected_sample_ids and not sample_set.get("sample_ids"):
        sample_set["sample_ids"] = list(context.expected_sample_ids)
    taxonomy_seed = payload.setdefault("taxonomy_seed", {})
    if isinstance(taxonomy_seed, dict):
        candidate_codes = _seed_codes(taxonomy_seed)
        if not taxonomy_seed.get("candidate_codes"):
            taxonomy_seed["candidate_codes"] = sorted(candidate_codes)
    projection_seed = payload.setdefault("projection_seed", {})
    projections = projection_seed.get("projections") if isinstance(projection_seed, dict) else None
    if isinstance(projection_seed, dict) and isinstance(projections, list):
        projection_ids = [
            str(item.get("projection_id"))
            for item in projections
            if isinstance(item, Mapping) and str(item.get("projection_id", "")).strip()
        ]
        if not projection_seed.get("candidate_projection_ids"):
            projection_seed["candidate_projection_ids"] = projection_ids
        for projection in projections:
            if isinstance(projection, dict):
                _repair_seed_projection(projection, taxonomy_seed, sample_set)
    report_seed = payload.setdefault("user_report_samples_seed", {})
    if isinstance(report_seed, dict) and not str(report_seed.get("overview", "")).strip():
        report_seed["overview"] = str(sample_set.get("summary") or report_seed.get("report_purpose") or _DEFAULT_OVERVIEW)


def _seed_codes(taxonomy_seed: Mapping[str, Any]) -> set[str]:
    codes = {"other"}
    for section in ("domains", "document_types", "categories", "subcategories", "field_codes", "row_types", "cell_codes"):
        for item in taxonomy_seed.get(section, ()):
            if isinstance(item, Mapping) and str(item.get("code", "")).strip():
                codes.add(str(item["code"]))
            elif isinstance(item, str) and item.strip():
                codes.add(item)
    fallback = taxonomy_seed.get("fallback_codes")
    if isinstance(fallback, Mapping):
        codes.update(str(value) for value in fallback.values() if str(value).strip())
    return codes


def _codes_for_section(taxonomy_seed: Mapping[str, Any], section: str) -> list[str]:
    codes = []
    for item in taxonomy_seed.get(section, ()):
        if isinstance(item, Mapping) and str(item.get("code", "")).strip():
            codes.append(str(item["code"]))
        elif isinstance(item, str) and item.strip():
            codes.append(item)
    if section != "domains" and "other" not in codes:
        codes.append("other")
    return list(dict.fromkeys(codes))


def _repair_seed_projection(
    projection: dict[str, Any],
    taxonomy_seed: Mapping[str, Any],
    sample_set: Mapping[str, Any],
) -> None:
    projection["status"] = _STATUS_ALIASES.get(str(projection.get("status") or "").strip().lower(), projection.get("status") or "draft")
    defaults = {
        "domain_ids": _codes_for_section(taxonomy_seed, "domains") or _classification_codes(sample_set, "domain_codes"),
        "include_document_types": _codes_for_section(taxonomy_seed, "document_types") or ["other"],
        "include_categories": _codes_for_section(taxonomy_seed, "categories") or ["other"],
        "include_subcategories": _codes_for_section(taxonomy_seed, "subcategories") or ["other"],
        "include_field_codes": _codes_for_section(taxonomy_seed, "field_codes") or ["other"],
        "include_row_types": _codes_for_section(taxonomy_seed, "row_types") or ["other"],
        "include_cell_codes": _codes_for_section(taxonomy_seed, "cell_codes") or ["other"],
    }
    for key, fallback in defaults.items():
        if not projection.get(key):
            projection[key] = fallback
    routing = projection.setdefault("routing", {})
    if isinstance(routing, dict):
        routing.setdefault("example_document_types", [code for code in projection.get("include_document_types", []) if code != "other"][:3])
        routing.setdefault("section_roles", _nested_list(sample_set, "structure", "section_roles") or ["other"])
        routing.setdefault("party_roles", _nested_list(sample_set, "structure", "party_roles") or ["other"])
    lexicon = projection.setdefault("routing_lexicon", {})
    if isinstance(lexicon, dict):
        markers = _nested_list(sample_set, "signals", "text_markers")
        if not lexicon.get("text_markers"):
            lexicon["text_markers"] = markers
        if not lexicon.get("domain_markers"):
            lexicon["domain_markers"] = [{"domain_id": domain_id, "markers": markers[:5]} for domain_id in projection.get("domain_ids", [])]


def _classification_codes(sample_set: Mapping[str, Any], key: str) -> list[str]:
    classification = sample_set.get("classification")
    if not isinstance(classification, Mapping):
        return []
    values = classification.get(key)
    return [str(item) for item in values] if isinstance(values, list) else []


def _nested_list(value: Mapping[str, Any], section: str, key: str) -> list[str]:
    child = value.get(section)
    if not isinstance(child, Mapping) or not isinstance(child.get(key), list):
        return []
    return [str(item) for item in child[key]]


_DEFAULT_OVERVIEW = "Sample analysis produced a normalized seed for downstream taxonomy and projection authoring."

__all__ = ["repair_sample_analysis_seed"]
