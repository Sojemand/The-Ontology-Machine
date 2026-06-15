"""Named result types for normalizer workflow outcomes."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalizationResult:
    input_path: str
    output_path: str | None
    status: str
    needs_review: bool
    duration_ms: int
    message: str = ""
    review_reason: str = ""
