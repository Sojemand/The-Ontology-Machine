"""Rendering adapters for PDFs and raster image sources."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .policy import _can_copy_losslessly, _prefer_lossless_pdf_page, _prefer_lossless_pil_image

logger = logging.getLogger(__name__)


def _render_pdf_via_pymupdf(
    pdf_path: Path,
    dest_dir: Path,
    dpi: int,
    quality: int,
) -> list[str] | None:
    """Render PDF pages at fixed fidelity via PyMuPDF only."""
    try:
        import fitz

        fitz.TOOLS.mupdf_display_errors(False)
    except ImportError:
        return None

    doc = None
    try:
        doc = fitz.open(str(pdf_path))
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        paths: list[str] = []
        for index, page in enumerate(doc, start=1):
            prefer_png = _prefer_lossless_pdf_page(page)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            suffix = ".png" if prefer_png else ".jpg"
            out_path = dest_dir / f"page_{index:03d}{suffix}"
            if prefer_png:
                pix.save(str(out_path))
            else:
                pix.save(str(out_path), output="jpeg", jpg_quality=quality)
            paths.append(str(out_path.resolve()))
        return paths
    except Exception as exc:
        logger.warning("pymupdf failed for %s: %s", pdf_path.name, exc)
        return None
    finally:
        if doc:
            doc.close()


def _render_image(image_path: Path, dest_dir: Path, quality: int) -> list[str]:
    """Convert or copy image files into one page asset per frame."""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed, skipping image conversion")
        return []

    try:
        with Image.open(str(image_path)) as image:
            frame_count = getattr(image, "n_frames", 1)
            paths: list[str] = []
            for frame_index in range(frame_count):
                if frame_count > 1:
                    image.seek(frame_index)
                frame = image.copy()
                prefer_png = _prefer_lossless_pil_image(frame)
                suffix = ".png" if prefer_png else ".jpg"
                out_path = dest_dir / f"page_{frame_index + 1:03d}{suffix}"
                if frame_count == 1 and _can_copy_losslessly(image_path, suffix):
                    shutil.copy2(image_path, out_path)
                else:
                    _save_pil_image(frame, out_path, quality)
                paths.append(str(out_path.resolve()))
        return paths
    except Exception as exc:
        logger.warning("Image conversion failed for %s: %s", image_path.name, exc)
        return []


def _save_pil_image(image, out_path: Path, quality: int) -> None:
    """Save PIL images into the requested output format."""
    if out_path.suffix.lower() == ".png":
        image.save(str(out_path), "PNG")
        return
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(str(out_path), "JPEG", quality=quality, subsampling=0)
