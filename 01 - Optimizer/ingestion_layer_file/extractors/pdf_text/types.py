"""Typed carriers for the built-in PDF extractor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PdfTextLineSnapshot:
    text: str


@dataclass
class PdfTextBlockSnapshot:
    text: str


@dataclass
class PdfPageSnapshot:
    page_number: int
    text: str
    text_blocks: list[PdfTextBlockSnapshot] = field(default_factory=list)
    text_lines: list[PdfTextLineSnapshot] = field(default_factory=list)
    tables: list[Any] = field(default_factory=list)
    has_images: bool = False


@dataclass
class PdfDocumentSnapshot:
    page_count: int
    pages: list[PdfPageSnapshot] = field(default_factory=list)
    pdf_version: str | None = None
    has_annotations: bool = False


@dataclass
class PdfCounters:
    total_chars: int = 0
    text_block_count: int = 0
    table_cell_count: int = 0
    scan_pages: int = 0
    has_images: bool = False


@dataclass
class PdfMetadataSummary:
    page_count: int
    is_scanned: bool
    has_images: bool
    text_density: str
    avg_chars_per_page: float
    text_block_count: int
    table_cell_count: int
    pdf_version: str | None
    has_annotations: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_count": self.page_count,
            "is_scanned": self.is_scanned,
            "has_images": self.has_images,
            "text_density": self.text_density,
            "avg_chars_per_page": round(self.avg_chars_per_page, 1),
            "text_block_count": self.text_block_count,
            "table_cell_count": self.table_cell_count,
            "pdf_version": self.pdf_version,
            "has_annotations": self.has_annotations,
        }


class PdfStageError(RuntimeError):
    """Stage-labelled extractor failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
