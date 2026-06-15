"""Side-effect free free-text match policy."""
from __future__ import annotations

import math
import re
from typing import Any

from ...models.coercion import normalize_text, number_variants, parse_date
from ...models.config import MatchConfig
from ...models.types import PreparedFreeText


def _prepared_free_text(value: PreparedFreeText | Any) -> PreparedFreeText:
    if isinstance(value, PreparedFreeText):
        return value
    return PreparedFreeText.from_value(value)


def _has_token(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    pattern = rf"(^|[^0-9a-z]){re.escape(needle)}([^0-9a-z]|$)"
    return re.search(pattern, haystack) is not None


def match_number(value: int | float, free_text: PreparedFreeText | str, tolerance: float) -> bool:
    prepared = _prepared_free_text(free_text)
    if not prepared.is_present:
        return False
    expected = float(value)
    if not math.isfinite(expected):
        return False
    for candidate in prepared.numeric_candidates:
        if abs(candidate - expected) <= tolerance + 1e-9:
            return True
    for variant in number_variants(expected):
        if not variant.isdigit() and _has_token(prepared.normalized, normalize_text(variant)):
            return True
    return False


def match_date(value: str, free_text: PreparedFreeText | str) -> bool:
    prepared = _prepared_free_text(free_text)
    if not prepared.is_present:
        return False
    parsed = parse_date(value)
    if not parsed:
        return False
    variants = {
        parsed.strftime("%Y-%m-%d"),
        parsed.strftime("%d.%m.%Y"),
        parsed.strftime("%d.%m.%y"),
        parsed.strftime("%d/%m/%Y"),
        parsed.strftime("%d-%m-%Y"),
    }
    return any(normalize_text(variant) in prepared.normalized for variant in variants)


def match_string(value: str, free_text: PreparedFreeText | str, cfg: MatchConfig) -> bool:
    prepared = _prepared_free_text(free_text)
    needle = normalize_text(value)
    if not needle:
        return True
    if needle in prepared.normalized:
        return True
    compact_needle = re.sub(r"[^0-9a-z]+", "", needle)
    return len(compact_needle) >= cfg.min_compact_length and compact_needle in prepared.compact


def matches_free_text(value: Any, free_text: PreparedFreeText | str, cfg: MatchConfig) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return match_string(str(value).lower(), free_text, cfg)
    if isinstance(value, (int, float)):
        return match_number(value, free_text, cfg.number_tolerance_absolute)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return True
        return match_date(stripped, free_text) if parse_date(stripped) else match_string(stripped, free_text, cfg)
    return False


__all__ = ["match_date", "match_number", "match_string", "matches_free_text"]
