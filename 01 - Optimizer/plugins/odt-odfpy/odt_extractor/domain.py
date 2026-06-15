"""Pure block and metadata projection for the odt-odfpy extractor."""
from __future__ import annotations

from . import policy
from .types import OdtDocumentSnapshot, OdtProjection


def project_document(snapshot: OdtDocumentSnapshot) -> OdtProjection:
    blocks: list[dict[str, object]] = []
    headings: list[str] = []
    heading_count = 0
    paragraph_count = 0
    narrative_index = 0
    word_count = 0

    for text_node in snapshot.text_nodes:
        word_count += len(text_node.text.split())
        if text_node.kind == "h":
            headings.append(text_node.text)
            blocks.append(
                {
                    "id": f"heading_{heading_count}",
                    "type": "header",
                    "position": _position(paragraph_index=narrative_index),
                    "value": text_node.text,
                    "value_type": "text",
                    "formatting": {"bold": True, "font_size": None, "heading_level": policy.coerce_heading_level(text_node.outline_level)},
                    "confidence": None,
                }
            )
            heading_count += 1
        else:
            blocks.append(
                {
                    "id": f"para_{paragraph_count}",
                    "type": "paragraph",
                    "position": _position(paragraph_index=narrative_index),
                    "value": text_node.text,
                    "value_type": "text",
                    "formatting": None,
                    "confidence": None,
                }
            )
            paragraph_count += 1
        narrative_index += 1

    for cell in snapshot.table_cells:
        word_count += len(cell.text.split())
        blocks.append(
            {
                "id": f"table{cell.table_index}_R{cell.row_index}_C{cell.col_index}",
                "type": "table_row",
                "position": _position(row=cell.row_index, col=cell.col_index, table_index=cell.table_index),
                "value": cell.text,
                "value_type": "text",
                "formatting": None,
                "confidence": None,
            }
        )

    return OdtProjection(
        blocks=blocks,
        metadata={
            "paragraph_count": paragraph_count,
            "heading_count": heading_count,
            "headings": policy.summarize_headings(headings),
            "table_count": snapshot.table_count,
            "table_col_count": list(snapshot.table_col_counts) or None,
            "word_count": word_count,
            "has_tables": snapshot.table_count > 0,
            "author": snapshot.author,
        },
    )


def _position(
    *,
    paragraph_index: int | None = None,
    row: int | None = None,
    col: int | None = None,
    table_index: int | None = None,
) -> dict[str, int | None]:
    return {
        "sheet": None,
        "row": row,
        "col": col,
        "col_letter": None,
        "page": None,
        "paragraph_index": paragraph_index,
        "table_index": table_index,
    }
