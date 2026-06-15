"""Pure block coercion for raw plugin output."""
from __future__ import annotations

from ...models import BlockFormatting, BlockPosition, DataBlock


def parse_blocks(processor, raw_blocks: list[dict[str, object]]) -> list[DataBlock]:
    blocks: list[DataBlock] = []
    max_blocks = max(0, int(processor._config.max_blocks_per_file))
    for index, raw_block in enumerate(raw_blocks):
        if max_blocks and index >= max_blocks:
            break
        block = raw_block if isinstance(raw_block, dict) else {}
        position = _build_position(block.get("position"))
        blocks.append(
            DataBlock(
                id=str(block.get("id", f"B{index}")),
                type=str(block.get("type", "paragraph")),
                position=position,
                value=block.get("value"),
                value_type=str(block.get("value_type", "text")),
                formatting=_build_formatting(block.get("formatting")),
                page_span=_build_page_span(block.get("page_span")),
                origin=_build_origin(block.get("origin")),
                confidence=block.get("confidence"),
            )
        )
    return blocks


def _build_position(raw_position: object) -> BlockPosition:
    data = raw_position if isinstance(raw_position, dict) else {}
    return BlockPosition(
        sheet=data.get("sheet"),
        row=data.get("row"),
        col=data.get("col"),
        col_letter=data.get("col_letter"),
        page=data.get("page"),
        paragraph_index=data.get("paragraph_index"),
        table_index=data.get("table_index"),
    )


def _build_formatting(raw_formatting: object) -> BlockFormatting | None:
    data = raw_formatting if isinstance(raw_formatting, dict) else None
    if data is None:
        return None
    merged_with = data.get("merged_with")
    if merged_with is None and data.get("merged_range"):
        merged_with = [data.get("merged_range")]
    return BlockFormatting(
        bold=data.get("bold"),
        font_size=data.get("font_size"),
        merged_with=merged_with,
    )


def _build_page_span(raw_page_span: object) -> list[int] | None:
    if not isinstance(raw_page_span, list):
        return None
    page_span: list[int] = []
    for item in raw_page_span:
        try:
            page_span.append(int(item))
        except (TypeError, ValueError):
            continue
    return page_span or None


def _build_origin(raw_origin: object) -> dict[str, object] | None:
    if not isinstance(raw_origin, dict):
        return None
    return dict(raw_origin)
