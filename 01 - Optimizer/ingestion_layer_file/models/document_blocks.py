"""Block dataclasses for file optimizer document payloads."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .document_formats import ValueType


@dataclass
class BlockPosition:
    sheet: str | None = None
    row: int | None = None
    col: int | None = None
    col_letter: str | None = None
    page: int | None = None
    paragraph_index: int | None = None
    table_index: int | None = None


@dataclass
class BlockFormatting:
    bold: bool | None = None
    font_size: float | None = None
    merged_with: list[str] | None = None


@dataclass
class DataBlock:
    id: str
    type: str
    position: BlockPosition
    value: Any = None
    value_type: str = ValueType.TEXT
    formatting: BlockFormatting | None = None
    page_span: list[int] | None = None
    origin: dict[str, Any] | None = None
    confidence: float | None = None


@dataclass
class NormalizedBlock:
    id: str
    type: str
    page: int
    text: str
    paragraph_index: int | None = None
    table_index: int | None = None
    row: int | None = None
    col: int | None = None
    formatting: BlockFormatting | None = None
    confidence: float | None = None
    source_block_id: str | None = None

    def to_data_block(self) -> DataBlock:
        return DataBlock(
            id=self.id,
            type=self.type,
            position=BlockPosition(
                page=self.page,
                paragraph_index=self.paragraph_index,
                table_index=self.table_index,
                row=self.row,
                col=self.col,
            ),
            value=self.text,
            value_type=ValueType.TEXT,
            formatting=self.formatting,
            confidence=self.confidence,
        )
