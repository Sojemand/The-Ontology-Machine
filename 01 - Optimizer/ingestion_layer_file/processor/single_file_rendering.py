"""Rendering helpers for explicit single-file processor targets."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from ..models import BlockPosition, DataBlock, FileFormat
from ..rendering.page_extract import apply_page_attribution

_OFFICE_FORMATS = {FileFormat.DOC, FileFormat.DOCX, FileFormat.ODT, FileFormat.RTF}
_TEXT_VIEWER_FORMATS = {FileFormat.TEXT, FileFormat.CONFIG}


def render_document_assets(
    processor,
    file_path: Path,
    *,
    fmt: str,
    source_blocks: list,
    page_images_dir: Path,
) -> tuple[list[str], list, str, str]:
    surface_module = sys.modules[__package__]
    if fmt == FileFormat.PDF:
        image_paths = surface_module.render_pdf_to_images(file_path, page_images_dir=page_images_dir, config=processor._config)
        return image_paths, _ensure_native_page_positions(source_blocks, total_pages=len(image_paths)), "pdf_direct", "source_pdf"
    rendered = surface_module.render_non_pdf_document(
        source_blocks,
        file_path,
        page_images_dir=page_images_dir,
        config=processor._config,
    )
    image_paths = list(rendered.image_paths)
    rendered_blocks = list(rendered.blocks)
    render_route = rendered.render_route or ("office_to_pdf" if fmt in _OFFICE_FORMATS else "html_viewer_pdf")
    pagination_source = rendered.pagination_source or ("office_export_pdf" if fmt in _OFFICE_FORMATS else "viewer_pdf")
    if fmt in _OFFICE_FORMATS:
        if len(image_paths) > 1:
            return image_paths, rendered_blocks, render_route, pagination_source
        return image_paths, _ensure_native_page_positions(source_blocks, total_pages=len(image_paths)), render_route, pagination_source
    if fmt in _TEXT_VIEWER_FORMATS and len(image_paths) > 1 and rendered_blocks:
        return image_paths, rendered_blocks, render_route, pagination_source
    attributed_blocks = apply_page_attribution(
        source_blocks,
        rendered_blocks,
        total_pages=len(image_paths),
    )
    return image_paths, attributed_blocks, render_route, pagination_source


def _ensure_native_page_positions(source_blocks: list[DataBlock], *, total_pages: int) -> list[DataBlock]:
    normalized: list[DataBlock] = []
    for block in source_blocks:
        cloned = copy.deepcopy(block)
        if cloned.position.page is None:
            if total_pages == 1:
                cloned.position = cloned.position or BlockPosition()
                cloned.position.page = 1
            else:
                raise RuntimeError(
                    f"File-Pfad fail-closed: born-digital PDF-Block {block.id!r} hat keine native Seite."
                )
        normalized.append(cloned)
    return normalized
