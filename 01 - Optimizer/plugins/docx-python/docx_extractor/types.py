"""Typed carriers for the staged docx-python extractor."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreparedSource:
    source: Path
    original_suffix: str
    cleanup_dirs: tuple[Path, ...] = ()


@dataclass(frozen=True)
class WordParagraphSnapshot:
    index: int
    text: str
    style_name: str
    bold: bool
    font_size: float | None


@dataclass(frozen=True)
class WordTableCellSnapshot:
    table_index: int
    row_index: int
    col_index: int
    text: str


@dataclass(frozen=True)
class WordOcrBlockSnapshot:
    id: str
    type: str
    text: str
    paragraph_index: int
    confidence: float | None = None


@dataclass(frozen=True)
class WordDocumentSnapshot:
    paragraphs: tuple[WordParagraphSnapshot, ...] = ()
    table_cells: tuple[WordTableCellSnapshot, ...] = ()
    table_count: int = 0
    table_col_counts: tuple[int, ...] = ()
    has_images: bool = False
    image_count: int = 0
    author: str | None = None
    last_modified_by: str | None = None
    has_track_changes: bool = False
    ocr_blocks: tuple[WordOcrBlockSnapshot, ...] = ()
    ocr_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WordProjection:
    blocks: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class WordStageError(RuntimeError):
    """Stage-labelled extractor failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
