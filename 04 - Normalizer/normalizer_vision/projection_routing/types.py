"""Named carriers for projection-hint routing."""
from __future__ import annotations

from dataclasses import dataclass

from ..taxonomy import TaxonomyProfile


@dataclass(frozen=True, slots=True)
class ProjectionHint:
    projection_id: str | None
    confidence: float | None
    reason: str | None
    matched_signals: list[str]


@dataclass(frozen=True, slots=True)
class ProjectionSelection:
    profile: TaxonomyProfile
    mode: str
    hint_projection_id: str | None
    hint_confidence: float | None
    catalog_version: str | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "hint_projection_id": self.hint_projection_id,
            "hint_confidence": self.hint_confidence,
            "catalog_version": self.catalog_version,
            "reason": self.reason,
        }
