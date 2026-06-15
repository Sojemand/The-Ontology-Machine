"""Pure block and metadata projection for the rtf-reader extractor."""
from __future__ import annotations

from . import policy
from .types import RtfDocumentSnapshot, RtfProjection


def project_document(snapshot: RtfDocumentSnapshot) -> RtfProjection:
    paragraphs = _split_paragraphs(snapshot.plain_text)
    blocks: list[dict[str, object]] = []
    headings: list[str] = []
    word_count = 0
    paragraph_count = 0
    heading_count = 0

    for block_idx, paragraph in enumerate(paragraphs):
        word_count += len(paragraph.split())
        block_type = "paragraph"
        if policy.is_heading(paragraph):
            block_type = "header"
            heading_count += 1
            headings.append(paragraph)
        else:
            paragraph_count += 1
        blocks.append(_build_block(block_idx, block_type, paragraph))

    return RtfProjection(
        blocks=blocks,
        metadata={
            "word_count": word_count,
            "line_count": snapshot.line_count,
            "paragraph_count": paragraph_count,
            "heading_count": heading_count,
            "headings": ", ".join(headings) if headings else None,
            "has_tables": False,
        },
    )


def _split_paragraphs(plain_text: str) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in plain_text.split("\n\n"):
        cleaned = paragraph.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def _build_block(block_idx: int, block_type: str, value: str) -> dict[str, object]:
    return {
        "id": f"rtf_b{block_idx}",
        "type": block_type,
        "position": _position(block_idx),
        "value": value,
        "value_type": "text",
        "formatting": None,
        "confidence": None,
    }


def _position(paragraph_index: int) -> dict[str, int | None]:
    return {
        "sheet": None,
        "row": None,
        "col": None,
        "col_letter": None,
        "page": None,
        "paragraph_index": paragraph_index,
        "table_index": None,
    }
