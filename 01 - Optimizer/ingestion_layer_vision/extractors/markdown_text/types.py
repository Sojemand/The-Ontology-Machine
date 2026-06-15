"""Typed parse outcomes for the markdown/text extractor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseMetrics:
    heading_count: int = 0
    code_block_count: int = 0
    paragraph_count: int = 0
    list_item_count: int = 0
    headings: list[str] = field(default_factory=list)

    def heading_summary(self, limit: int = 200) -> str:
        summary = ", ".join(self.headings)
        if len(summary) > limit:
            return summary[:limit]
        return summary


@dataclass
class ParseOutcome:
    blocks: list[dict[str, Any]] = field(default_factory=list)
    metrics: ParseMetrics = field(default_factory=ParseMetrics)
