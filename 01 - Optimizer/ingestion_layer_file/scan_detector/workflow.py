"""Workflow for publishing stable per-page vision assets."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from .adapter import _render_image
from .policy import IMAGE_EXTS, _safe_asset_key
from .repository import (
    _cleanup_stage_dir,
    _clear_existing_asset_dir,
    _create_stage_dir,
    _publish_stage_dir,
)

logger = logging.getLogger(__name__)


def render_page_images(
    file_path: str,
    output_dir: str,
    *,
    asset_key: str | None = None,
    dpi: int = 150,
    quality: int = 95,
) -> list[str]:
    """
    Create high-fidelity page images for vision calls.

    - PDF: render each page without downscaling; prefer PNG for text/line-art pages
    - Image files: preserve the original frame fidelity where possible
    """
    fp = Path(file_path)
    ext = fp.suffix.lower()
    dest_dir = Path(output_dir) / "page_images" / _safe_asset_key(asset_key, fp.name)

    if ext == ".pdf":
        render = lambda stage_dir: _render_pdf_pages(fp, stage_dir, dpi, quality)
    elif ext in IMAGE_EXTS:
        render = lambda stage_dir: _render_image(fp, stage_dir, quality)
    else:
        _clear_existing_asset_dir(dest_dir)
        logger.warning("render_page_images: unsupported format %s for %s", ext, fp.name)
        return []

    stage_dir = _create_stage_dir(dest_dir)
    try:
        paths = render(stage_dir)
        if not paths:
            raise RuntimeError(f"Keine Vision-Assets erzeugt fuer {fp.name}")
        return _publish_stage_dir(stage_dir, dest_dir, paths)
    except Exception:
        _cleanup_stage_dir(stage_dir)
        raise


def _render_pdf_pages(pdf_path: Path, dest_dir: Path, dpi: int, quality: int) -> list[str]:
    paths = _surface_module()._render_pdf_via_pymupdf(pdf_path, dest_dir, dpi, quality)
    if paths is not None:
        return paths
    logger.warning(
        "PDF rendering failed for %s: pymupdf unavailable or failed",
        pdf_path.name,
    )
    return []


def _surface_module():
    return sys.modules[__package__]
