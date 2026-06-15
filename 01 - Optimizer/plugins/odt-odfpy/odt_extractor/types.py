"""Typed carriers for the staged odt-odfpy extractor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OdtTextSnapshot:
    kind: str
    text: str
    outline_level: str | None = None


@dataclass(frozen=True)
class OdtTableCellSnapshot:
    table_index: int
    row_index: int
    col_index: int
    text: str


@dataclass(frozen=True)
class OdtDocumentSnapshot:
    text_nodes: tuple[OdtTextSnapshot, ...] = ()
    table_cells: tuple[OdtTableCellSnapshot, ...] = ()
    table_count: int = 0
    table_col_counts: tuple[int, ...] = ()
    author: str | None = None


@dataclass(frozen=True)
class OdtProjection:
    blocks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OdtStageError(RuntimeError):
    """Stage-labelled extractor failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
