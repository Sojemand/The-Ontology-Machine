from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .tool_handler_deps import _add_optional, _invoke_product, _positive_int, _positive_or_zero_int
from .tool_handler_source_fit_context import active_release_summary, projection_matches
from .tool_handler_source_fit_review import recommended_refinement_kernel_tool, refinement_safe_next_kernel_tools
from .tool_handler_source_fit_terms import (
    candidate_field_labels,
    compact_text,
    document_concepts,
    flatten_text,
    limit_unique,
    normalized_terms,
    observed_field_evidence,
    source_sample_summary,
    unsupported,
)
from .tool_handler_source_sample_set_messages import compatibility_payload, refinement_request, sample_set_warnings, user_message
from .tool_handler_source_sample_set_paths import active_input_folder_sample_paths


def review_source_sample_set_taxonomy_coverage(arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _positive_int(arguments["timeout_seconds"], "timeout_seconds") if arguments.get("timeout_seconds") not in (None, "") else None
    release = _active_release(arguments, timeout)
    paths = active_input_folder_sample_paths(arguments)
    samples = [_inspect_sample(path, arguments, timeout) for path in paths]
    aggregate = _aggregate_samples(release, samples)
    delta_type = _sample_set_delta_type(aggregate)
    compatibility = compatibility_payload(delta_type, len(samples))
    return {
        "status": "ok",
        "question_contract": "document_set_release_refinement",
        "corpus_db_path": str(arguments.get("corpus_db_path") or release.get("corpus_db_path") or ""),
        "artifact_folder": str(arguments.get("artifact_folder") or ""),
        "active_release": release,
        "sample_set": aggregate["sample_set"],
        "taxonomy_coverage": aggregate["taxonomy_coverage"] | {"delta_type": delta_type},
        "working_release_refinement_request": refinement_request(arguments, release, aggregate, delta_type),
        "compatibility_review": compatibility,
        "recommended_first_kernel_tool": recommended_refinement_kernel_tool(delta_type),
        "safe_next_kernel_tools": refinement_safe_next_kernel_tools(delta_type),
        "user_message_de": user_message(delta_type, aggregate, compatibility),
    }


def _active_release(arguments: dict[str, Any], timeout: int | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": "read_active_semantic_release"}
    _add_optional(payload, arguments, "corpus_db_path")
    return active_release_summary(_invoke_product("corpus_builder", payload, timeout=timeout))


def _inspect_sample(path: Path, arguments: dict[str, Any], timeout: int | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": "inspect_source_document_sample", "source_document_path": str(path)}
    for key in ("max_excerpt_chars", "cleanup_days"):
        if key in arguments and arguments[key] not in (None, ""):
            payload[key] = _positive_or_zero_int(arguments[key], key) if key == "cleanup_days" else _positive_int(arguments[key], key)
    if timeout is not None:
        payload["timeout_seconds"] = timeout
    return _invoke_product("orchestrator", payload, timeout=timeout)


def _aggregate_samples(release: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    release_terms = normalized_terms([*release.get("known_terms", []), *flatten_text(release.get("projections"))])
    field_counts: Counter[str] = Counter()
    marker_counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    marker_evidence: dict[str, list[str]] = defaultdict(list)
    summaries, matches, clusters = [], [], Counter()
    for sample in samples:
        concepts = document_concepts(sample)
        fields = _sample_fields(sample, concepts, release_terms)
        markers = unsupported([*concepts["headings"], *concepts["candidate_markers"]], release_terms, limit=16)
        summary = source_sample_summary(sample, concepts)
        summaries.append(summary)
        matches.extend(projection_matches(release.get("projections", []), compact_text(sample)))
        cluster = str(summary.get("signals", {}).get("estimated_document_type") or "unknown") or "unknown"
        clusters[cluster] += 1
        path = str(sample.get("source_document_path") or "")
        for field in fields:
            field_counts[field] += 1
            evidence[field].append(path)
        for marker in markers:
            marker_counts[marker] += 1
            marker_evidence[marker].append(path)
    return _aggregate_payload(samples, summaries, field_counts, marker_counts, evidence, marker_evidence, matches, clusters)


def _sample_fields(sample: dict[str, Any], concepts: dict[str, list[str]], release_terms: set[str]) -> list[str]:
    field_evidence = observed_field_evidence(concepts)
    unsupported_fields = unsupported(field_evidence, release_terms, limit=12)
    return candidate_field_labels(unsupported_fields, field_evidence)


def _aggregate_payload(samples: list[dict[str, Any]], summaries: list[dict[str, Any]], field_counts: Counter[str], marker_counts: Counter[str],
                       evidence: dict[str, list[str]], marker_evidence: dict[str, list[str]], matches: list[dict[str, Any]],
                       clusters: Counter[str]) -> dict[str, Any]:
    sample_count = len(samples)
    common_min = max(2, int(sample_count * 0.6 + 0.999)) if sample_count > 1 else 1
    field_groups = _groups(field_counts, evidence, common_min)
    marker_groups = _groups(marker_counts, marker_evidence, common_min)
    return {
        "sample_set": {
            "sample_count": sample_count,
            "source_document_paths": [str(sample.get("source_document_path") or "") for sample in samples],
            "document_type_clusters": [{"cluster": key, "sample_count": count} for key, count in clusters.most_common()],
            "sample_summaries": summaries,
            "warnings": sample_set_warnings(sample_count, clusters, field_groups),
        },
        "taxonomy_coverage": {
            "basis": "active semantic release plus aggregated local source sample inspection",
            "observed_content_evidence": {
                "field_like_or_heading_phrases": limit_unique(_flatten_summary_hint(summaries, "field_like_phrases") + _flatten_summary_hint(summaries, "headings"), limit=60),
                "routing_or_topic_markers": limit_unique(_flatten_summary_hint(summaries, "candidate_markers"), limit=60),
                "ignored_technical_hints": limit_unique(_flatten_summary_hint(summaries, "ignored_technical_hints"), limit=60),
            },
            "candidate_projection_matches": matches[:20],
            "recurring_field_candidates": field_groups["common"],
            "subgroup_field_candidates": field_groups["subgroup"],
            "one_off_field_candidates": field_groups["one_off"],
            "recurring_routing_markers": marker_groups["common"],
            "subgroup_routing_markers": marker_groups["subgroup"],
            "one_off_routing_markers": marker_groups["one_off"],
            "requires_agent_field_proposal": bool(field_groups["common"] or field_groups["subgroup"] or field_groups["one_off"]),
        },
    }


def _groups(counts: Counter[str], evidence: dict[str, list[str]], common_min: int) -> dict[str, list[dict[str, Any]]]:
    groups = {"common": [], "subgroup": [], "one_off": []}
    for label, count in counts.most_common():
        item = {"label": label, "sample_count": count, "evidence_paths": limit_unique(evidence[label], limit=6)}
        if count >= common_min:
            groups["common"].append(item)
        elif count >= 2:
            groups["subgroup"].append(item)
        else:
            groups["one_off"].append(item)
    return groups


def _flatten_summary_hint(summaries: list[dict[str, Any]], key: str) -> list[str]:
    return [
        str(item)
        for summary in summaries
        for item in (summary.get("content_hints", {}).get(key, []) if isinstance(summary.get("content_hints"), dict) else [])
        if str(item or "").strip()
    ]


def _sample_set_delta_type(aggregate: dict[str, Any]) -> str:
    coverage = aggregate["taxonomy_coverage"]
    if coverage["recurring_field_candidates"] or coverage["subgroup_field_candidates"]:
        return "sample_set_taxonomy_fields_likely"
    if coverage["recurring_routing_markers"] or coverage["subgroup_routing_markers"]:
        return "sample_set_projection_or_routing_gap_likely"
    if coverage["one_off_field_candidates"]:
        return "one_off_candidates_need_more_evidence"
    return "no_structural_gap_detected"


__all__ = [name for name in globals() if not name.startswith("__")]
