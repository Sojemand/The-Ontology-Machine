from __future__ import annotations

from typing import Any

from .tool_handler_source_fit_context import projection_matches, source_release_context
from .tool_handler_source_fit_review import fit_warnings, taxonomy_coverage_review
from .tool_handler_source_fit_terms import compact_text


def assess_source_document_fit(arguments: dict[str, Any]) -> dict[str, Any]:
    context = source_release_context(arguments)
    release_summary = context["active_release"]
    sample_result = context["source_sample"]
    matches = projection_matches(release_summary.get("projections", []), compact_text(sample_result))
    coverage = taxonomy_coverage_review(release_summary, sample_result, matches, arguments)
    return {
        "status": "ok",
        "source_document_path": context["source_document_path"],
        "corpus_db_path": str(arguments.get("corpus_db_path") or release_summary.get("corpus_db_path") or ""),
        "active_release": release_summary,
        "source_sample": sample_result,
        "projection_fit": {
            "checked": True,
            "basis": "active semantic release plus source document sample inspection",
            "candidate_projection_matches": matches,
            "warnings": fit_warnings(release_summary, sample_result),
        },
        "coverage_refinement_advice": coverage["refinement_advice"],
    }


def review_source_document_taxonomy_coverage(arguments: dict[str, Any]) -> dict[str, Any]:
    context = source_release_context(arguments)
    release_summary = context["active_release"]
    sample_result = context["source_sample"]
    matches = projection_matches(release_summary.get("projections", []), compact_text(sample_result))
    coverage = taxonomy_coverage_review(release_summary, sample_result, matches, arguments)
    return {
        "status": "ok",
        "question_contract": "document_set_release_refinement",
        "source_document_path": context["source_document_path"],
        "corpus_db_path": str(arguments.get("corpus_db_path") or release_summary.get("corpus_db_path") or ""),
        "artifact_folder": str(arguments.get("artifact_folder") or ""),
        "active_release": release_summary,
        "source_sample": coverage["source_sample_summary"],
        "taxonomy_coverage": coverage["taxonomy_coverage"],
        "working_release_refinement_request": coverage["working_release_refinement_request"],
        "compatibility_review": coverage["compatibility_review"],
        "safe_next_kernel_tools": coverage["safe_next_kernel_tools"],
        "user_message_de": coverage["user_message_de"],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
