"""Pure domain builders for blocks and raw extracts."""
from __future__ import annotations

from ..input_catalog import CatalogEntry
from ..models import (
    BlockFormatting,
    BlockPosition,
    ContextInfo,
    DataBlock,
    ExtractionInfo,
    RawExtract,
    SourceInfo,
)

def build_extract(
    processor,
    *,
    entry: CatalogEntry,
    file_path,
    filename: str,
    ext: str,
    fmt: str,
    relative_path: str,
    size: int,
    result,
    plugin_name: str,
    blocks: list[DataBlock],
    vision: bool,
    scan_detected: bool,
    ocr_was_used: bool,
    image_paths: list[str],
    content_hash: str,
    ingest_id: str = "",
    page_number: int | None = None,
    total_pages: int | None = None,
    source_path_text: str | None = None,
    source_filename: str | None = None,
    source_relative_path: str | None = None,
) -> RawExtract:
    public_path = source_path_text or str(file_path)
    public_filename = source_filename or filename
    public_relative_path = source_relative_path or relative_path
    source = SourceInfo(
        ingest_id=ingest_id,
        owner_id=None,
        path=public_path,
        filename=public_filename,
        file_ext=ext,
        format=fmt,
        size_bytes=size,
        created=entry.created,
        modified=entry.modified,
        content_hash=content_hash,
        relative_path=public_relative_path,
    )
    manifest = processor._plugin_mgr.get_manifest(plugin_name)
    plugin_version = manifest.version if manifest else ""
    metadata = dict(result.metadata)
    if vision and image_paths and "page_count" not in metadata:
        metadata["page_count"] = len(image_paths)
    return RawExtract(
        source=source,
        context=ContextInfo(),
        extraction=ExtractionInfo(
            plugin_name=plugin_name,
            plugin_version=plugin_version,
            processing_time_ms=result.processing_time_ms,
            block_count=len(blocks),
            ocr_used=ocr_was_used,
        ),
        metadata=metadata,
        needs_llm_vision=vision,
        image_paths=image_paths,
        blocks=blocks,
        is_scan=scan_detected,
        page_number=page_number,
        total_pages=total_pages,
    )


def parse_blocks(processor, raw_blocks: list[dict]) -> list[DataBlock]:
    del processor
    blocks: list[DataBlock] = []
    for index, raw_block in enumerate(raw_blocks):
        pos_data = raw_block.get("position", {})
        fmt_data = raw_block.get("formatting")
        formatting = None
        if fmt_data:
            merged_with = fmt_data.get("merged_with")
            if merged_with is None and fmt_data.get("merged_range"):
                merged_with = [fmt_data.get("merged_range")]
            formatting = BlockFormatting(
                bold=fmt_data.get("bold"),
                font_size=fmt_data.get("font_size"),
                merged_with=merged_with,
            )
        value = raw_block.get("value")
        blocks.append(
            DataBlock(
                id=raw_block.get("id", f"B{index}"),
                type=raw_block.get("type", "paragraph"),
                position=BlockPosition(
                    sheet=pos_data.get("sheet"),
                    row=pos_data.get("row"),
                    col=pos_data.get("col"),
                    col_letter=pos_data.get("col_letter"),
                    page=pos_data.get("page"),
                    paragraph_index=pos_data.get("paragraph_index"),
                    table_index=pos_data.get("table_index"),
                ),
                value=value,
                value_type=raw_block.get("value_type", "text"),
                layout_label=raw_block.get("layout_label"),
                formatting=formatting,
                confidence=raw_block.get("confidence"),
            )
        )
    return blocks
