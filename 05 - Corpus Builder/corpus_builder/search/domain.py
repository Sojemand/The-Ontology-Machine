"""Pure search result mapping and hybrid score composition."""

from __future__ import annotations

from collections.abc import Mapping

from ..models.results import SearchResult
from . import policy
from .types import HybridScoreEntry


def build_fts_result(row: Mapping[str, object]) -> SearchResult:
    raw_rank = row["fts_rank"]
    score = abs(float(raw_rank)) if raw_rank else 0.0
    return SearchResult(
        document_id=str(row["id"]),
        title=_optional_text(_lookup(row, "result_title")),
        description=_optional_text(_lookup(row, "result_description")),
        snippet=_optional_text(_lookup(row, "snippet")),
        score=score,
        source="fts",
    )


def build_vector_result(hit: Mapping[str, object]) -> SearchResult:
    return SearchResult(
        document_id=str(hit["document_id"]),
        title=_optional_text(hit.get("title")),
        description=_optional_text(hit.get("description")),
        snippet=_optional_text(hit.get("snippet")),
        score=float(hit["similarity"]),
        source="vector",
    )


def merge_hybrid_results(
    fts_results: list[SearchResult],
    vector_results: list[SearchResult],
    *,
    fts_weight: float,
    vec_weight: float,
    top_k: int,
    normalize_fts_scores: bool = True,
) -> list[SearchResult]:
    scored: dict[str, HybridScoreEntry] = {}
    max_fts_score = max((result.score for result in fts_results), default=0.0) or 1.0

    for result in fts_results:
        scored[result.document_id] = HybridScoreEntry(
            document_id=result.document_id,
            title=result.title,
            description=result.description,
            snippet=result.snippet,
            fts=policy.normalize_fts_score(
                result.score,
                max_score=max_fts_score,
                enabled=normalize_fts_scores,
            ),
        )

    for result in vector_results:
        entry = scored.get(result.document_id)
        if entry is None:
            entry = HybridScoreEntry(
                document_id=result.document_id,
                title=result.title,
                description=result.description,
                snippet=result.snippet,
            )
            scored[result.document_id] = entry
        elif entry.snippet is None and result.snippet:
            entry.snippet = result.snippet
        entry.vec = result.score

    merged = [
        SearchResult(
            document_id=entry.document_id,
            title=entry.title,
            description=entry.description,
            snippet=entry.snippet,
            score=(fts_weight * entry.fts) + (vec_weight * entry.vec),
            source="hybrid",
        )
        for entry in scored.values()
    ]
    merged.sort(key=lambda item: item.score, reverse=True)
    return merged[:top_k]


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _lookup(mapping: Mapping[str, object], key: str) -> object | None:
    try:
        return mapping[key]
    except KeyError:
        return None
