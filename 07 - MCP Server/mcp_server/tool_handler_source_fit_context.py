from __future__ import annotations

from typing import Any

from .tool_handler_deps import _add_optional, _invoke_product, _positive_int, _positive_or_zero_int, _required_text
from .tool_handler_source_fit_terms import flatten_text, limit_unique


def source_release_context(arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _positive_int(arguments["timeout_seconds"], "timeout_seconds") if arguments.get("timeout_seconds") not in (None, "") else None
    release_payload: dict[str, Any] = {"action": "read_active_semantic_release"}
    _add_optional(release_payload, arguments, "corpus_db_path")
    release_result = _invoke_product("corpus_builder", release_payload, timeout=timeout)
    sample_payload = sample_payload_from_arguments(arguments, timeout)
    sample_result = _invoke_product("orchestrator", sample_payload, timeout=timeout)
    return {
        "source_document_path": sample_payload["source_document_path"],
        "active_release": active_release_summary(release_result),
        "source_sample": sample_result,
    }


def sample_payload_from_arguments(arguments: dict[str, Any], timeout: int | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": "inspect_source_document_sample", "source_document_path": _required_text(arguments, "source_document_path")}
    _add_optional(payload, arguments, "sample_label")
    for key in ("max_excerpt_chars", "cleanup_days"):
        if key in arguments and arguments[key] not in (None, ""):
            payload[key] = _positive_or_zero_int(arguments[key], key) if key == "cleanup_days" else _positive_int(arguments[key], key)
    if timeout is not None:
        payload["timeout_seconds"] = timeout
    return payload


def active_release_summary(result: dict[str, Any]) -> dict[str, Any]:
    detail = result.get("detail") if isinstance(result.get("detail"), dict) else result
    release = detail.get("release") if isinstance(detail, dict) and isinstance(detail.get("release"), dict) else {}
    projections = release.get("projections") if isinstance(release.get("projections"), list) else []
    projection_ids = release.get("projection_ids") or [item.get("projection_id") for item in projections if isinstance(item, dict)]
    status = detail.get("status") if isinstance(detail.get("status"), dict) else {}
    snapshot = detail.get("active_snapshot") if isinstance(detail.get("active_snapshot"), dict) else {}
    return {
        "release_id": str(detail.get("release_id") or release.get("release_id") or ""),
        "release_version": str(detail.get("release_version") or release.get("release_version") or ""),
        "fingerprint": str(detail.get("fingerprint") or release.get("fingerprint") or ""),
        "master_taxonomy_release_id": str(detail.get("master_taxonomy_release_id") or release.get("master_taxonomy_release_id") or ""),
        "runtime_locale": str(release.get("runtime_locale") or status.get("active_runtime_locale") or ""),
        "active_snapshot_id": str(snapshot.get("snapshot_id") or ""),
        "runtime_truth_source": str(status.get("runtime_truth_source") or ""),
        "corpus_db_path": str(detail.get("corpus_db_path") or result.get("corpus_db_path") or ""),
        "projection_ids": [str(item) for item in projection_ids or [] if str(item).strip()],
        "projections": [projection_summary(item) for item in projections if isinstance(item, dict)],
        "known_terms": release_terms(release),
    }


def projection_summary(projection: dict[str, Any]) -> dict[str, Any]:
    routing = projection.get("routing") if isinstance(projection.get("routing"), dict) else {}
    return {
        "projection_id": str(projection.get("projection_id") or ""),
        "label": str(projection.get("label") or projection.get("name") or ""),
        "routing": {
            "when_to_use": routing.get("when_to_use") or "",
            "avoid_when": routing.get("avoid_when") or "",
            "example_document_types": routing.get("example_document_types") or [],
            "surface_signals": routing.get("surface_signals") or {},
        },
    }


def projection_matches(projections: list[dict[str, Any]], sample_text: str) -> list[dict[str, Any]]:
    lowered = sample_text.casefold()
    matches = []
    for projection in projections:
        hits = [term for term in projection_terms(projection) if len(term) >= 4 and term.casefold() in lowered]
        if hits:
            matches.append({"projection_id": projection.get("projection_id", ""), "label": projection.get("label", ""), "matched_terms": sorted(set(hits))[:12]})
    return matches


def projection_terms(projection: dict[str, Any]) -> list[str]:
    routing = projection.get("routing") if isinstance(projection.get("routing"), dict) else {}
    signals = routing.get("surface_signals") if isinstance(routing.get("surface_signals"), dict) else {}
    terms = [str(projection.get("projection_id") or ""), str(projection.get("label") or "")]
    terms.extend(flatten_text(routing.get("when_to_use")))
    terms.extend(flatten_text(routing.get("example_document_types")))
    terms.extend(flatten_text(signals))
    return [term.strip() for term in terms if term and term.strip()]


def release_terms(release: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    terms.extend(flatten_text(release.get("projection_ids")))
    terms.extend(flatten_text(release.get("master_taxonomy_id")))
    terms.extend(flatten_text(release.get("master_taxonomy_version")))
    for projection in release.get("projections") or []:
        if isinstance(projection, dict):
            terms.extend(projection_terms(projection_summary(projection)))
            terms.extend(flatten_text(projection.get("text")))
            terms.extend(flatten_text(projection.get("texts")))
    terms.extend(master_term_texts(release.get("master_taxonomy")))
    terms.extend(master_term_texts(release.get("runtime_semantic_assets")))
    return limit_unique(terms, limit=240)


def master_term_texts(value: Any) -> list[str]:
    if not isinstance(value, (dict, list)):
        return []
    result: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            result.extend(flatten_text(item) if str(key) in {"term_id", "code", "label", "text", "description", "value_type"} else master_term_texts(item))
    else:
        for item in value:
            result.extend(master_term_texts(item))
    return result


__all__ = [name for name in globals() if not name.startswith("__")]
