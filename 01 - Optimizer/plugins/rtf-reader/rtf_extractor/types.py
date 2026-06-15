"""Typed carriers for the staged rtf-reader extractor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RtfDocumentSnapshot:
    plain_text: str
    line_count: int


@dataclass(frozen=True)
class RtfProjection:
    blocks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RtfStageError(RuntimeError):
    """Stage-labelled extractor failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
