"""Pure Word block and metadata projection."""
from __future__ import annotations

from . import policy
from .types import WordDocumentSnapshot, WordProjection


def project_document(snapshot: WordDocumentSnapshot) -> WordProjection:
    heading_titles = policy.heading_titles(snapshot.paragraphs)
    blocks: list[dict[str, object]] = []
    paragraph_count = 0
    heading_count = 0

    for paragraph in snapshot.paragraphs:
        if policy.is_heading_style(paragraph.style_name):
            blocks.append(
                {
                    "id": f"heading_{heading_count}",
                    "type": "header",
                    "position": _position(paragraph_index=heading_count),
                    "value": paragraph.text,
                    "value_type": "text",
                    "formatting": {"bold": True, "font_size": None},
                    "confidence": None,
                }
            )
            heading_count += 1
            continue

        blocks.append(
            {
                "id": f"para_{paragraph_count}",
                "type": "paragraph",
                "position": _position(paragraph_index=paragraph_count),
                "value": paragraph.text,
                "value_type": "text",
                "formatting": policy.formatting_payload(
                    bold=paragraph.bold,
                    font_size=paragraph.font_size,
                ),
                "confidence": None,
            }
        )
        paragraph_count += 1

    ocr_heading_titles: list[str] = []
    for ocr_block in snapshot.ocr_blocks:
        if ocr_block.type == "header":
            blocks.append(
                {
                    "id": ocr_block.id,
                    "type": "header",
                    "position": _position(paragraph_index=ocr_block.paragraph_index),
                    "value": ocr_block.text,
                    "value_type": "text",
                    "formatting": {"bold": True, "font_size": None},
                    "confidence": ocr_block.confidence,
                }
            )
            heading_count += 1
            ocr_heading_titles.append(ocr_block.text)
            continue

        blocks.append(
            {
                "id": ocr_block.id,
                "type": ocr_block.type,
                "position": _position(paragraph_index=ocr_block.paragraph_index),
                "value": ocr_block.text,
                "value_type": "text",
                "formatting": None,
                "confidence": ocr_block.confidence,
            }
        )
        paragraph_count += 1

    for cell in snapshot.table_cells:
        blocks.append(
            {
                "id": f"table{cell.table_index}_R{cell.row_index}_C{cell.col_index}",
                "type": "table_row",
                "position": _position(
                    row=cell.row_index,
                    col=cell.col_index,
                    table_index=cell.table_index,
                ),
                "value": cell.text,
                "value_type": "text",
                "formatting": None,
                "confidence": None,
            }
        )

    all_heading_titles = heading_titles + ocr_heading_titles
    metadata = {
        "paragraph_count": paragraph_count,
        "heading_count": heading_count,
        "table_count": snapshot.table_count,
        "table_col_count": list(snapshot.table_col_counts) or None,
        "headings": policy.summarize_headings(all_heading_titles),
        "heading_keywords": all_heading_titles,
        "has_tables": snapshot.table_count > 0,
        "has_images": snapshot.has_images,
        "word_count": sum(len(paragraph.text.split()) for paragraph in snapshot.paragraphs) + sum(len(block.text.split()) for block in snapshot.ocr_blocks),
        "image_count": snapshot.image_count,
        "author": snapshot.author,
        "last_modified_by": snapshot.last_modified_by,
        "has_track_changes": snapshot.has_track_changes,
    }
    metadata.update(snapshot.ocr_metadata)
    return WordProjection(blocks=blocks, metadata=metadata)


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
