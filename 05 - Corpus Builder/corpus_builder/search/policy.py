"""Policy defaults for search limits, filter matching, and hybrid scoring."""

from __future__ import annotations


def normalize_positive_int(value: object, *, fallback: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(1, normalized)


def hybrid_candidate_limit(top_k: object, *, candidate_multiplier: object = 2) -> int:
    multiplier = normalize_positive_int(candidate_multiplier, fallback=2)
    return normalize_positive_int(top_k, fallback=10) * multiplier


def filter_operator(value: object) -> str:
    return "like" if "%" in str(value) else "eq"


def normalize_fts_score(score: float, *, max_score: float, enabled: bool = True) -> float:
    if not enabled:
        return score
    if max_score <= 0:
        return 0.0
    return score / max_score
