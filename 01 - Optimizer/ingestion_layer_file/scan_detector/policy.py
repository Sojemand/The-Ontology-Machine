"""Pure scan and format heuristics for the scan detector."""
from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
_ASSET_SAFE_CHAR_RE = re.compile(r"[^A-Za-z0-9._-]+")


def is_scan(plugin_result: dict, file_ext: str) -> bool:
    """Detect whether a PDF is likely a scan."""
    del file_ext
    meta = plugin_result.get("metadata", {})
    if meta.get("needs_ocr") is True:
        return True
    page_count = meta.get("page_count", 1)
    total_text = sum(
        len(str(block.get("value", "")))
        for block in plugin_result.get("blocks", [])
        if block.get("value")
    )
    if total_text / max(page_count, 1) < 50:
        return True
    return meta.get("has_images") is True


def should_use_vision(file_ext: str, is_scan_result: bool) -> bool:
    """Decide whether `needs_llm_vision=true` should be set."""
    normalized = file_ext.lower()
    return normalized in IMAGE_EXTS or (normalized == ".pdf" and is_scan_result)


def _prefer_lossless_pdf_page(page) -> bool:
    """Prefer PNG for text/vector pages and JPEG for image-heavy pages."""
    try:
        has_raster_images = bool(page.get_images(full=True))
    except Exception:
        has_raster_images = False
    try:
        text = (page.get_text("text") or "").strip()
    except Exception:
        text = ""
    if has_raster_images:
        return False
    return bool(text) or not has_raster_images


def _prefer_lossless_pil_image(image) -> bool:
    """Use PNG for low-color or grayscale inputs, JPEG otherwise."""
    if getattr(image, "mode", "") in {"1", "L", "LA", "P"}:
        return True
    sample = image.copy()
    try:
        sample.thumbnail((256, 256))
    except Exception:
        return False
    if sample.mode not in {"RGB", "RGBA", "L", "P"}:
        sample = sample.convert("RGB")
    try:
        colors = sample.getcolors(maxcolors=256)
    except Exception:
        colors = None
    return colors is not None and len(colors) <= 128


def _can_copy_losslessly(image_path: Path, suffix: str) -> bool:
    source_suffix = image_path.suffix.lower()
    if suffix == ".png":
        return source_suffix == ".png"
    if suffix == ".jpg":
        return source_suffix in {".jpg", ".jpeg"}
    return False


def _safe_asset_key(asset_key: str | None, fallback_name: str) -> str:
    candidate = str(asset_key or fallback_name).replace("\\", "/")
    candidate = _ASSET_SAFE_CHAR_RE.sub("_", candidate).strip("._-")
    if candidate:
        return candidate
    fallback = _ASSET_SAFE_CHAR_RE.sub("_", fallback_name).strip("._-")
    return fallback or "page_asset"
