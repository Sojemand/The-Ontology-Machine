"""Source-first non-PDF rendering workflow."""
from __future__ import annotations

from pathlib import Path

from ..models import IngestionConfig, RenderPlanResult
from .html_viewer import TEXT_VIEWER_EXTS, render_text_like_document_to_pdf
from .page_extract import extract_page_reference_blocks
from .office_export import OFFICE_EXTS, export_office_document_to_pdf
from .pdf_pages import render_pdf_to_images


def render_non_pdf_document(
    blocks,
    source_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    asset_key: str | None = None,
    page_images_dir: str | Path | None = None,
    config: IngestionConfig,
) -> RenderPlanResult:
    del blocks
    source = Path(source_path)
    ext = source.suffix.lower()
    if ext in OFFICE_EXTS:
        intermediate_pdf = export_office_document_to_pdf(source)
        render_route = "office_to_pdf"
        pagination_source = "office_export_pdf"
    elif ext in TEXT_VIEWER_EXTS:
        intermediate_pdf = render_text_like_document_to_pdf(source, config)
        render_route = "html_viewer_pdf"
        pagination_source = "viewer_pdf"
    else:
        raise ValueError(f"Kein Source-First-Renderer fuer {ext} definiert")

    intermediate_path = Path(intermediate_pdf)
    try:
        image_paths = render_pdf_to_images(
            intermediate_path,
            output_dir,
            asset_key=asset_key,
            page_images_dir=page_images_dir,
            config=config,
        )
        reference_blocks = extract_page_reference_blocks(intermediate_path, config)
        return RenderPlanResult(
            blocks=reference_blocks,
            page_count=len(image_paths),
            image_paths=image_paths,
            intermediate_pdf_path=str(intermediate_path),
            render_route=render_route,
            pagination_source=pagination_source,
        )
    finally:
        intermediate_path.unlink(missing_ok=True)
