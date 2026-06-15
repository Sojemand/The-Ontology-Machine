"""Shared parsing helpers for raw-backed numeric/date claims."""
from __future__ import annotations

import math
import re

from ..models.coercion import parse_date
from .numeric_claim_numbers import parse_claim_number, parse_native_number
from .numeric_claim_patterns import EMBEDDED_DATE_PATTERNS, EMBEDDED_NUMERIC_TOKEN_RE
from .numeric_claim_quality import prepare_claim_text, strength_for_number, strength_for_quality
from .numeric_claim_split import split_numeric_candidate_claims
from .numeric_claim_types import ClaimEvidence, ParsedClaim, stronger_claim_strength


def iter_scalar_claims(value: str) -> list[ParsedClaim]:
    text, quality_flags = prepare_claim_text(value)
    text = text.strip()
    if not text:
        return []
    parsed_date = parse_date(text)
    if parsed_date is not None:
        return [
            ParsedClaim(
                kind="date",
                raw_value=parsed_date.strftime("%Y-%m-%d"),
                display_value=text,
                strength=strength_for_quality("strong", quality_flags),
                quality_flags=frozenset(quality_flags),
            )
        ]
    parsed_number = parse_native_number(text)
    if parsed_number is not None and math.isfinite(parsed_number):
        return [
            ParsedClaim(
                kind="number",
                raw_value=parsed_number,
                display_value=text,
                strength=strength_for_quality("strong", quality_flags),
                quality_flags=frozenset(quality_flags),
            )
        ]
    return []


def iter_embedded_claims(value: str, *, context_hint: str = "") -> list[ParsedClaim]:
    text, quality_flags = prepare_claim_text(value)
    if not text.strip():
        return []
    claims: list[ParsedClaim] = []
    consumed = [False] * len(text)
    for pattern in EMBEDDED_DATE_PATTERNS:
        for match in pattern.finditer(text):
            _append_embedded_date_claim(claims, consumed, match, quality_flags)
    masked = "".join(" " if consumed[index] else char for index, char in enumerate(text))
    for match in EMBEDDED_NUMERIC_TOKEN_RE.finditer(masked):
        claims.extend(
            _claims_from_numeric_match(
                text=masked,
                match=match,
                context_hint=context_hint,
                quality_flags=quality_flags,
            )
        )
    return claims


def record_claim(
    claims: dict[str, ClaimEvidence],
    *,
    kind: str,
    raw_value: str | float,
    field_path: str,
    display_value: str,
    strength: str = "strong",
    source_kind: str = "",
    quality_flags: set[str] | frozenset[str] = frozenset(),
) -> None:
    key = claim_key(kind, raw_value)
    claim = claims.get(key)
    if claim is None:
        claim = ClaimEvidence(kind=kind, key=key, raw_value=raw_value, strength=strength)
        claims[key] = claim
    else:
        claim.strength = stronger_claim_strength(claim.strength, strength)
    claim.field_paths.add(field_path)
    if display_value not in claim.display_values:
        claim.display_values.append(display_value)
    if source_kind:
        claim.source_kinds.add(source_kind)
    claim.quality_flags.update(quality_flags)


def claim_key(kind: str, raw_value: str | float) -> str:
    if kind == "date":
        return f"date:{raw_value}"
    number = float(raw_value)
    formatted = format(number, ".12f").rstrip("0").rstrip(".")
    return f"num:{formatted or '0'}"


def _append_embedded_date_claim(
    claims: list[ParsedClaim],
    consumed: list[bool],
    match: re.Match[str],
    quality_flags: set[str],
) -> None:
    candidate = match.group(0)
    parsed_date = parse_date(candidate)
    if parsed_date is None:
        return
    claims.append(
        ParsedClaim(
            kind="date",
            raw_value=parsed_date.strftime("%Y-%m-%d"),
            display_value=candidate,
            strength=strength_for_quality("strong", quality_flags),
            quality_flags=frozenset(quality_flags),
        )
    )
    for index in range(match.start(), match.end()):
        consumed[index] = True


def _claims_from_numeric_match(
    *,
    text: str,
    match: re.Match[str],
    context_hint: str,
    quality_flags: set[str],
) -> list[ParsedClaim]:
    candidate = match.group(0)
    parsed_number, candidate_flags = parse_claim_number(candidate)
    if parsed_number is None:
        return split_numeric_candidate_claims(
            candidate=candidate,
            text=text,
            start=match.start(),
            end=match.end(),
            context_hint=context_hint,
            quality_flags=quality_flags,
        )
    if not math.isfinite(parsed_number):
        return []
    flags = set(quality_flags)
    flags.update(candidate_flags)
    return [
        ParsedClaim(
            kind="number",
            raw_value=parsed_number,
            display_value=candidate,
            strength=strength_for_number(
                text=text,
                start=match.start(),
                end=match.end(),
                display_value=candidate,
                parsed_number=parsed_number,
                context_hint=context_hint,
                quality_flags=flags,
            ),
            quality_flags=frozenset(flags),
        )
    ]


__all__ = [
    "ParsedClaim",
    "claim_key",
    "iter_embedded_claims",
    "iter_scalar_claims",
    "parse_claim_number",
    "parse_native_number",
    "prepare_claim_text",
    "record_claim",
]
