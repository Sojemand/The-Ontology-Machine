"""Workflow surface for source-first HTML viewer rendering."""
from __future__ import annotations

from pathlib import Path

from ...models import IngestionConfig
from . import adapter, domain
from .types import HtmlViewerStageError, TEXT_VIEWER_EXTS, ViewerLayout


def render_text_like_document_to_pdf(source_path: str | Path, config: IngestionConfig) -> str:
    source = adapter.read_source(source_path)
    layout = _layout_from_config(config)
    _validate_source(source.ext)
    _validate_layout(layout)
    document = domain.build_document_html(source)
    return adapter.render_html_to_pdf(document, layout, domain.build_viewer_css(layout))


def _layout_from_config(config: IngestionConfig) -> ViewerLayout:
    try:
        return ViewerLayout(
            page_margin_pt=float(config.page_margin_pt),
            default_font_size_pt=float(config.default_font_size_pt),
            code_font_size_pt=float(config.code_font_size_pt),
            heading_font_size_pt=float(config.heading_font_size_pt),
        )
    except Exception as exc:
        raise HtmlViewerStageError("workflow.validation", f"ungueltige Viewer-Konfiguration: {exc}") from exc


def _validate_source(ext: str) -> None:
    if ext in TEXT_VIEWER_EXTS:
        return
    suffix = ext or "<ohne Endung>"
    raise HtmlViewerStageError("workflow.validation", f"Kein HTML-Viewer fuer {suffix} definiert")


def _validate_layout(layout: ViewerLayout) -> None:
    min_page_side = min(layout.page_width_pt, layout.page_height_pt)
    if layout.page_margin_pt <= 0:
        raise HtmlViewerStageError("workflow.validation", "page_margin_pt muss groesser als 0 sein")
    if layout.page_margin_pt * 2 >= min_page_side:
        raise HtmlViewerStageError("workflow.validation", "page_margin_pt ist groesser als der nutzbare Seitenraum")
    if min(layout.default_font_size_pt, layout.code_font_size_pt, layout.heading_font_size_pt) <= 0:
        raise HtmlViewerStageError("workflow.validation", "Viewer-Schriftgroessen muessen groesser als 0 sein")
