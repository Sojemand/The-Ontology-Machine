"""Rendering adapters for PDFs and raster image sources."""
from __future__ import annotations

import logging
from pathlib import Path

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
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY, alpha=False)
            out_path = dest_dir / f"page_{index:03d}.png"
            _save_pixmap_png(pix, out_path, quality, dpi)
            paths.append(str(out_path.resolve()))
        return paths
    except Exception as exc:
        logger.warning("pymupdf failed for %s: %s", pdf_path.name, exc)
        return None
    finally:
        if doc:
            doc.close()


def _render_image(image_path: Path, dest_dir: Path, quality: int, dpi: int) -> list[str]:
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
                frame = image.copy().convert("L")
                out_path = dest_dir / f"page_{frame_index + 1:03d}.png"
                _save_pil_image(frame, out_path, quality, dpi=dpi)
                paths.append(str(out_path.resolve()))
        return paths
    except Exception as exc:
        logger.warning("Image conversion failed for %s: %s", image_path.name, exc)
        return []


def _save_pixmap_png(pix, out_path: Path, quality: int, dpi: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        if hasattr(pix, "set_dpi"):
            pix.set_dpi(dpi, dpi)
        pix.save(str(out_path))
        return
    image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    _save_pil_image(image, out_path, quality, dpi=dpi)


def _save_pil_image(image, out_path: Path, quality: int, *, dpi: int) -> None:
    """Save PIL images into the requested output format."""
    del quality
    if image.mode != "L":
        image = image.convert("L")
    image.save(str(out_path), "PNG", optimize=True, dpi=(dpi, dpi))
