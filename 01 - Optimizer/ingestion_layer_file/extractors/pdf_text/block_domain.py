"""Pure block factories for the built-in PDF extractor."""
from __future__ import annotations

from typing import Any

from .types import PdfPageSnapshot


def build_page_blocks(page: PdfPageSnapshot) -> tuple[list[dict[str, Any]], int, int]:
    if page.text_blocks:
        text_blocks = _build_text_blocks(page.page_number, page.text_blocks)
    elif page.text_lines:
        text_blocks = _build_text_blocks(page.page_number, page.text_lines)
    else:
        text_blocks = _build_paragraph_blocks(page.page_number, page.text)
    table_blocks = _build_table_blocks(page.page_number, page.tables)
    return text_blocks + table_blocks, len(text_blocks), len(table_blocks)


def _build_text_blocks(page_number: int, items: list[Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for paragraph_index, item in enumerate(items):
        text = str(getattr(item, "text", "") or "").strip()
        if not text:
            continue
        blocks.append(
            {
                "id": f"page{page_number}_para_{paragraph_index}",
                "type": "paragraph",
                "position": _build_position(page=page_number, paragraph_index=paragraph_index),
                "value": text,
                "value_type": "text",
                "formatting": None,
                "confidence": None,
            }
        )
    return blocks


def _build_paragraph_blocks(page_number: int, text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []

    paragraphs = [segment.strip() for segment in text.split("\n\n") if segment.strip()] or [stripped]
    return [
        {
            "id": f"page{page_number}_para_{paragraph_index}",
            "type": "paragraph",
            "position": _build_position(page=page_number, paragraph_index=paragraph_index),
            "value": paragraph,
            "value_type": "text",
            "formatting": None,
            "confidence": None,
        }
        for paragraph_index, paragraph in enumerate(paragraphs)
    ]


def _build_table_blocks(page_number: int, tables: list[Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        for row_index, row in enumerate(table):
            for col_index, cell_value in enumerate(row):
                if cell_value is None:
                    continue
                blocks.append(
                    {
                        "id": f"page{page_number}_table{table_index}_R{row_index}_C{col_index}",
                        "type": "table_row",
                        "position": _build_position(
                            page=page_number,
                            row=row_index,
                            col=col_index,
                            table_index=table_index,
                        ),
                        "value": str(cell_value),
                        "value_type": "text",
                        "formatting": None,
                        "confidence": None,
                    }
                )
    return blocks


def _build_position(
    *,
    page: int,
    paragraph_index: int | None = None,
    row: int | None = None,
    col: int | None = None,
    table_index: int | None = None,
) -> dict[str, Any]:
    return {
        "sheet": None,
        "row": row,
        "col": col,
        "col_letter": None,
        "page": page,
        "paragraph_index": paragraph_index,
        "table_index": table_index,
    }
