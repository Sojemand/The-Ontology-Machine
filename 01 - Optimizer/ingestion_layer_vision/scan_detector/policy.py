"""Pure scan and format heuristics for the scan detector."""
from __future__ import annotations

import re

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
_ASSET_SAFE_CHAR_RE = re.compile(r"[^A-Za-z0-9._-]+")


def is_scan(plugin_result: dict, file_ext: str, *, min_chars_per_page: int = 50, use_has_images: bool = True) -> bool:
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
    if total_text / max(page_count, 1) < max(int(min_chars_per_page), 1):
        return True
    return bool(meta.get("has_images")) if use_has_images else False


def should_use_vision(
    file_ext: str,
    is_scan_result: bool,
    *,
    images_always_vision: bool = True,
    pdf_scans_use_vision: bool = True,
) -> bool:
    """Decide whether `needs_llm_vision=true` should be set."""
    normalized = file_ext.lower()
    if normalized in IMAGE_EXTS:
        return bool(images_always_vision)
    return normalized == ".pdf" and bool(pdf_scans_use_vision) and is_scan_result


def _safe_asset_key(asset_key: str | None, fallback_name: str) -> str:
    candidate = str(asset_key or fallback_name).replace("\\", "/")
    candidate = _ASSET_SAFE_CHAR_RE.sub("_", candidate).strip("._-")
    if candidate:
        return candidate
    fallback = _ASSET_SAFE_CHAR_RE.sub("_", fallback_name).strip("._-")
    return fallback or "page_asset"
