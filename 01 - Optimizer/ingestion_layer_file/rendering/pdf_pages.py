"""PDF page rendering and PDF block normalization."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import BlockType, DataBlock, IngestionConfig
from .repository import cleanup_stage_dir, create_stage_dir, publish_stage_dir


def render_pdf_to_images(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    asset_key: str | None = None,
    page_images_dir: str | Path | None = None,
    config: IngestionConfig,
) -> list[str]:
    import fitz

    pdf_path = Path(file_path)
    if page_images_dir is not None:
        dest_dir = Path(page_images_dir)
    elif output_dir is not None and asset_key:
        dest_dir = Path(output_dir) / "page_images" / asset_key
    else:
        raise ValueError("output_dir oder page_images_dir fehlt fuer render_pdf_to_images()")
    stage_dir = create_stage_dir(dest_dir)
    try:
        doc = fitz.open(str(pdf_path))
        try:
            paths: list[str] = []
            for index, page in enumerate(doc, start=1):
                image = _render_pdf_page_to_canvas(page, config)
                out_path = stage_dir / f"page_{index:03d}.png"
                image.save(out_path, "PNG", optimize=True)
                paths.append(str(out_path.resolve()))
        finally:
            doc.close()
        if not paths:
            raise OSError(f"Vision-Assets fehlen fuer {pdf_path}")
        return publish_stage_dir(stage_dir, dest_dir, paths)
    except Exception:
        cleanup_stage_dir(stage_dir)
        raise


def normalize_pdf_blocks(blocks: list[DataBlock]) -> list[DataBlock]:
    counters: dict[tuple[int, str], int] = {}
    normalized: list[DataBlock] = []
    for block in blocks:
        page = max(1, int(block.position.page or 1))
        block_type = block.type or BlockType.PARAGRAPH
        prefix = _block_prefix(block_type)
        sequence_key = (page, prefix)
        sequence = counters.get(sequence_key, 0)
        counters[sequence_key] = sequence + 1
        normalized.append(
            DataBlock(
                id=_pdf_block_id(page, block_type, block, sequence),
                type=BlockType.TABLE_CELL if _is_table_block(block) else block_type,
                position=block.position,
                value=_compact_text(block.value),
                value_type=block.value_type,
                formatting=block.formatting,
                confidence=block.confidence,
            )
        )
    return normalized


def _render_pdf_page_to_canvas(page, config: IngestionConfig):
    import fitz
    from PIL import Image

    width_px = config.render_width_px
    height_px = config.render_height_px
    rect = page.rect
    scale = min(width_px / max(rect.width, 1.0), height_px / max(rect.height, 1.0))
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    gray_pix = fitz.Pixmap(fitz.csGRAY, pix)
    image = Image.new("L", (width_px, height_px), color=255)
    rendered = Image.frombytes("L", [gray_pix.width, gray_pix.height], gray_pix.samples)
    offset_x = max(0, (width_px - rendered.width) // 2)
    offset_y = max(0, (height_px - rendered.height) // 2)
    image.paste(rendered, (offset_x, offset_y))
    return image


def _block_prefix(block_type: str) -> str:
    if block_type == BlockType.HEADER:
        return "heading"
    if block_type == BlockType.LIST_ITEM:
        return "list"
    if block_type == BlockType.CODE_BLOCK:
        return "code"
    if block_type == BlockType.CONFIG_SECTION:
        return "config"
    if block_type in {BlockType.TABLE_CELL, BlockType.TABLE_ROW}:
        return "table"
    return "para"


def _pdf_block_id(page: int, block_type: str, block: DataBlock, sequence: int) -> str:
    if _is_table_block(block):
        table_index = block.position.table_index or 0
        row = block.position.row or 0
        col = block.position.col or 0
        return f"page{page}_table{table_index}_r{row}_c{col}"
    return f"page{page}_{_block_prefix(block_type)}_{sequence}"


def _is_table_block(block: DataBlock) -> bool:
    return block.type in {BlockType.TABLE_CELL, BlockType.TABLE_ROW}


def _compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
