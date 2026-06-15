"""Workflow for creating run-scoped per-page vision assets."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from .adapter import _render_image
from .policy import IMAGE_EXTS, _safe_asset_key
from .repository import _cleanup_stage_dir, _clear_existing_asset_dir, _create_stage_dir, _publish_stage_dir

logger = logging.getLogger(__name__)


def render_page_assets(
    file_path: str,
    output_dir: str | None = None,
    *,
    page_assets_dir: str | None = None,
    asset_key: str | None = None,
    dpi: int = 150,
    quality: int = 95,
) -> list[str]:
    """
    Create grayscale page assets for vision calls.

    - PDF: render each page as 8-bit grayscale PNG
    - Image files: normalize each frame as 8-bit grayscale PNG
    """
    fp = Path(file_path)
    ext = fp.suffix.lower()
    if page_assets_dir:
        dest_dir = Path(page_assets_dir)
    elif output_dir:
        dest_dir = Path(output_dir) / "page_assets" / _safe_asset_key(asset_key, fp.name)
    else:
        raise ValueError("output_dir oder page_assets_dir fehlt fuer render_page_assets()")

    if ext == ".pdf":
        render = lambda stage_dir: _render_pdf_pages(fp, stage_dir, dpi, quality)
    elif ext in IMAGE_EXTS:
        render = lambda stage_dir: _render_image(fp, stage_dir, quality, dpi)
    else:
        _clear_existing_asset_dir(dest_dir)
        logger.warning("render_page_assets: unsupported format %s for %s", ext, fp.name)
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
