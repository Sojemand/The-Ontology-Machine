"""Stable rendering surface for page-image generation."""
from __future__ import annotations

from .health import renderer_dependency_selftests, renderer_selftest
from .pdf_pages import normalize_pdf_blocks, render_pdf_to_images
from .workflow import render_non_pdf_document

__all__ = [
    "normalize_pdf_blocks",
    "render_non_pdf_document",
    "render_pdf_to_images",
    "renderer_dependency_selftests",
    "renderer_selftest",
]
