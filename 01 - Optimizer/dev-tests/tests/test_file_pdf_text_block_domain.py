from __future__ import annotations

from ingestion_layer_file.extractors.pdf_text.block_domain import build_page_blocks
from ingestion_layer_file.extractors.pdf_text.types import PdfPageSnapshot, PdfTextBlockSnapshot, PdfTextLineSnapshot


def test_build_page_blocks_uses_pdf_text_blocks_without_geometry_payload() -> None:
    page = PdfPageSnapshot(
        page_number=1,
        text="dense legal text",
        text_blocks=[
            PdfTextBlockSnapshot(text="Left clause 1\nLeft clause 2"),
            PdfTextBlockSnapshot(text="Right clause 1\nRight clause 2"),
            PdfTextBlockSnapshot(text="Left clause 3\nLeft clause 4"),
        ],
        text_lines=[
            PdfTextLineSnapshot(text="Left clause 1"),
            PdfTextLineSnapshot(text="Right clause 1"),
        ],
    )

    blocks, text_count, table_count = build_page_blocks(page)

    assert text_count == 3
    assert table_count == 0
    assert [block["value"] for block in blocks] == [
        "Left clause 1\nLeft clause 2",
        "Right clause 1\nRight clause 2",
        "Left clause 3\nLeft clause 4",
    ]
    assert blocks[0]["position"] == {
        "sheet": None,
        "row": None,
        "col": None,
        "col_letter": None,
        "page": 1,
        "paragraph_index": 0,
        "table_index": None,
    }


def test_build_page_blocks_falls_back_to_lines_when_blocks_are_missing() -> None:
    page = PdfPageSnapshot(
        page_number=1,
        text="line fallback",
        text_lines=[
            PdfTextLineSnapshot(text="First line"),
            PdfTextLineSnapshot(text="Second line"),
        ],
    )

    blocks, text_count, _ = build_page_blocks(page)

    assert text_count == 2
    assert [block["value"] for block in blocks] == ["First line", "Second line"]


def test_build_page_blocks_keeps_section_marker_and_heading_together() -> None:
    page = PdfPageSnapshot(
        page_number=1,
        text="section heading",
        text_blocks=[
            PdfTextBlockSnapshot(text="§ 1\nGeltungsbereich/Vertragsabschluss"),
            PdfTextBlockSnapshot(text="1. Unsere Verkaufsbedingungen gelten ausschliesslich."),
            PdfTextBlockSnapshot(text="§ 6\nEigentumsvorbehalt"),
        ],
    )

    blocks, text_count, _ = build_page_blocks(page)

    assert text_count == 3
    values = [block["value"] for block in blocks]
    assert "§ 1\nGeltungsbereich/Vertragsabschluss" in values
    assert "§ 6\nEigentumsvorbehalt" in values
