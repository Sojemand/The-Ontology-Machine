from __future__ import annotations

import math
import re

from .numeric_claim_numbers import parse_claim_number
from .numeric_claim_quality import strength_for_number
from .numeric_claim_types import ParsedClaim


def split_numeric_candidate_claims(
    *,
    candidate: str,
    text: str,
    start: int,
    end: int,
    context_hint: str,
    quality_flags: set[str],
) -> list[ParsedClaim]:
    parts = [
        part.strip()
        for part in re.split(r"(?<=[0-9OoIl])[,;]\s+(?=[0-9OoIl])", candidate)
        if part.strip()
    ]
    if len(parts) <= 1:
        return []
    claims: list[ParsedClaim] = []
    search_from = start
    for part in parts:
        part_start = text.find(part, search_from, end)
        if part_start < 0:
            part_start = start
        claims.extend(_split_part_claim(part, text, part_start, context_hint, quality_flags))
        search_from = part_start + len(part)
    return claims


def _split_part_claim(
    part: str,
    text: str,
    part_start: int,
    context_hint: str,
    quality_flags: set[str],
) -> list[ParsedClaim]:
    part_end = part_start + len(part)
    parsed_number, candidate_flags = parse_claim_number(part)
    if parsed_number is None or not math.isfinite(parsed_number):
        return []
    flags = set(quality_flags)
    flags.update(candidate_flags)
    return [
        ParsedClaim(
            kind="number",
            raw_value=parsed_number,
            display_value=part,
            strength=strength_for_number(
                text=text,
                start=part_start,
                end=part_end,
                display_value=part,
                parsed_number=parsed_number,
                context_hint=context_hint,
                quality_flags=flags,
            ),
            quality_flags=frozenset(flags),
        )
    ]
