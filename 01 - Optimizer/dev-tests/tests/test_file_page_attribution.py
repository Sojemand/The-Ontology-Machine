from __future__ import annotations

import pytest

from ingestion_layer_file.models import BlockPosition, DataBlock
from ingestion_layer_file.rendering.page_extract import apply_page_attribution


def _block(block_id: str, text: str, *, page: int | None = None, paragraph_index: int | None = None) -> DataBlock:
    return DataBlock(
        id=block_id,
        type="paragraph",
        position=BlockPosition(page=page, paragraph_index=paragraph_index),
        value=text,
    )


def test_page_attribution_skips_renderer_title_before_first_plaintext_block():
    source_blocks = [
        _block("para_0", "First paragraph."),
        _block("para_1", "Second floor paragraph."),
        _block("para_2", "Razor-sharp edge."),
    ]
    reference_blocks = [
        _block("page1_para_0", "notes.txt", page=1, paragraph_index=0),
        _block("page1_para_1", "First paragraph.", page=1, paragraph_index=1),
        _block("page1_para_2", "Second \ufb02oor paragraph.", page=1, paragraph_index=2),
        _block("page1_para_3", "Razor-\nsharp edge.", page=1, paragraph_index=3),
    ]

    attributed = apply_page_attribution(source_blocks, reference_blocks, total_pages=2)

    assert [block.position.page for block in attributed] == [1, 1, 1]
    assert [block.position.paragraph_index for block in attributed] == [1, 2, 3]


def test_page_attribution_accepts_page_level_reference_chunks():
    source_blocks = [
        _block("para_0", "Mavis was now in her second year of retirement."),
        _block("para_1", "For decades, she worked for a large cleaning company\u2026 today."),
        _block("para_2", "As the days passed, she began to feel excited."),
    ]
    reference_blocks = [
        _block(
            "page1_para_0",
            "Mavis was now in her second year of retirement.\n"
            "For decades, she worked for a large cleaning company... today.",
            page=1,
            paragraph_index=0,
        ),
        _block(
            "page2_para_0",
            "As the days passed, she began to feel excited.",
            page=2,
            paragraph_index=0,
        ),
    ]

    attributed = apply_page_attribution(source_blocks, reference_blocks, total_pages=2)

    assert [block.position.page for block in attributed] == [1, 1, 2]
    assert [block.value for block in attributed] == [block.value for block in source_blocks]


def test_page_attribution_ignores_render_inserted_dash_spacing():
    source_blocks = [_block("para_0", "Tell us about yourself\u2014your previous jobs.")]
    reference_blocks = [
        _block("page1_para_0", "Tell us about yourself\u2014 your previous jobs.", page=1, paragraph_index=0)
    ]

    attributed = apply_page_attribution(source_blocks, reference_blocks, total_pages=2)

    assert attributed[0].position.page == 1
    assert attributed[0].value == source_blocks[0].value


def test_page_attribution_tracks_native_paragraph_across_page_level_chunks():
    source_blocks = [
        _block(
            "para_0",
            "Mavis found her first few weeks enjoyable yet tiring. "
            "She was working in what had once been the central library.",
        ),
        _block("para_1", "Days turned into weeks, and weeks into months."),
    ]
    reference_blocks = [
        _block(
            "page2_para_0",
            "Earlier page text. Mavis found her first few weeks enjoyable yet tiring. She was",
            page=2,
            paragraph_index=0,
        ),
        _block(
            "page3_para_0",
            "working in what had once been the central library. "
            "Days turned into weeks, and weeks into months. Later page text.",
            page=3,
            paragraph_index=0,
        ),
    ]

    attributed = apply_page_attribution(source_blocks, reference_blocks, total_pages=3)

    assert attributed[0].position.page == 2
    assert attributed[0].page_span == [2, 3]
    assert attributed[0].value == source_blocks[0].value
    assert attributed[1].position.page == 3
    assert attributed[1].page_span is None


def test_page_attribution_still_fails_when_text_cannot_be_matched():
    source_blocks = [_block("para_0", "Native text that never appears.")]
    reference_blocks = [_block("page1_para_0", "Different rendered page text.", page=1, paragraph_index=0)]

    with pytest.raises(RuntimeError, match="native page attribution"):
        apply_page_attribution(source_blocks, reference_blocks, total_pages=2)
