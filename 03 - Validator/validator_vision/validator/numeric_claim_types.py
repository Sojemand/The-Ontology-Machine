"""Named types for raw-backed numeric claim validation."""
from __future__ import annotations

from dataclasses import dataclass, field

CLAIM_STRENGTH_ORDER = {"weak": 0, "medium": 1, "strong": 2}


@dataclass(frozen=True)
class ParsedClaim:
    kind: str
    raw_value: str | float
    display_value: str
    strength: str = "strong"
    quality_flags: frozenset[str] = field(default_factory=frozenset)


@dataclass
class ClaimEvidence:
    kind: str
    key: str
    raw_value: str | float
    strength: str = "strong"
    field_paths: set[str] = field(default_factory=set)
    display_values: list[str] = field(default_factory=list)
    source_kinds: set[str] = field(default_factory=set)
    quality_flags: set[str] = field(default_factory=set)


def stronger_claim_strength(left: str, right: str) -> str:
    return left if CLAIM_STRENGTH_ORDER.get(left, 0) >= CLAIM_STRENGTH_ORDER.get(right, 0) else right


__all__ = ["ClaimEvidence", "CLAIM_STRENGTH_ORDER", "ParsedClaim", "stronger_claim_strength"]
