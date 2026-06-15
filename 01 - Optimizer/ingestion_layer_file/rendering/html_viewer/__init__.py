"""Stable surface for the HTML/CSS source-first viewer.

surface -> workflow -> adapter/domain -> types
"""
from __future__ import annotations

from pathlib import Path

from .domain import build_document_html
from .types import TEXT_VIEWER_EXTS, ViewerSource
from .workflow import render_text_like_document_to_pdf

__all__ = ["TEXT_VIEWER_EXTS", "render_text_like_document_to_pdf"]


def _build_document_html(source: Path, text: str) -> str:
    viewer_source = ViewerSource(
        path=Path(source),
        ext=Path(source).suffix.lower(),
        name=Path(source).name,
        text=text,
    )
    return build_document_html(viewer_source).html_payload
