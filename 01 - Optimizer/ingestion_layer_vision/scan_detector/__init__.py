"""Stable surface for scan detection and vision asset rendering."""
from __future__ import annotations

from .adapter import _render_pdf_via_pymupdf, _save_pil_image
from .policy import (
    IMAGE_EXTS,
    _safe_asset_key,
    is_scan,
    should_use_vision,
)
from .workflow import render_page_assets

__all__ = [
    "IMAGE_EXTS",
    "_render_pdf_via_pymupdf",
    "_safe_asset_key",
    "_save_pil_image",
    "is_scan",
    "render_page_assets",
    "should_use_vision",
]
