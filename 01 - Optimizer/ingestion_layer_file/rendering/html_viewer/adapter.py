"""Boundary adapters for HTML viewer I/O and PDF rendering."""
from __future__ import annotations

from pathlib import Path
import tempfile

from .types import HtmlViewerStageError, ViewerHtmlDocument, ViewerLayout, ViewerSource


def read_source(source_path: str | Path) -> ViewerSource:
    path = Path(source_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HtmlViewerStageError("adapter.read", str(exc)) from exc
    return ViewerSource(path=path, ext=path.suffix.lower(), name=path.name, text=text)


def render_html_to_pdf(document: ViewerHtmlDocument, layout: ViewerLayout, user_css: str) -> str:
    pdf_path: Path | None = None
    writer = None
    try:
        import fitz

        pdf_path = _create_temp_pdf_path()
        writer = fitz.DocumentWriter(str(pdf_path))
        story = fitz.Story(html=document.html_payload, user_css=user_css)
        mediabox = fitz.Rect(0, 0, layout.page_width_pt, layout.page_height_pt)
        content_rect = fitz.Rect(
            layout.page_margin_pt,
            layout.page_margin_pt,
            layout.page_width_pt - layout.page_margin_pt,
            layout.page_height_pt - layout.page_margin_pt,
        )
        story.write(writer, lambda _rect_num, _filled: (mediabox, content_rect, fitz.Identity))
        writer.close()
        return str(pdf_path)
    except HtmlViewerStageError:
        raise
    except Exception as exc:
        _cleanup_failed_render(pdf_path, writer)
        raise HtmlViewerStageError("adapter.render", str(exc)) from exc


def _create_temp_pdf_path() -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="file-optimizer-viewer-", suffix=".pdf", delete=False)
    handle.close()
    return Path(handle.name)


def _cleanup_failed_render(pdf_path: Path | None, writer) -> None:
    if writer is not None:
        try:
            writer.close()
        except Exception:
            pass
    if pdf_path is not None:
        pdf_path.unlink(missing_ok=True)
