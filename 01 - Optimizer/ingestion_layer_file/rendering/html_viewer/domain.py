"""Pure HTML document shaping for the source-first viewer."""
from __future__ import annotations

import html
from pathlib import Path
import re

from .markdown_domain import render_markdown_html
from .types import CONFIG_EXTS, MARKDOWN_EXTS, DocumentKind, ViewerHtmlDocument, ViewerLayout, ViewerSource


def build_document_html(source: ViewerSource) -> ViewerHtmlDocument:
    kind = _resolve_kind(source.ext)
    body_html = _build_body_html(kind, source.text)
    title = html.escape(source.name)
    html_payload = (
        "<html><body>"
        f"<article class=\"document {kind.value}\">"
        f"<header><div class=\"doc-name\">{title}</div></header>"
        f"{body_html}"
        "</article></body></html>"
    )
    return ViewerHtmlDocument(kind=kind, title=title, body_html=body_html, html_payload=html_payload)


def build_viewer_css(layout: ViewerLayout) -> str:
    heading_h1 = layout.heading_font_size_pt + 2
    heading_h2 = max(layout.heading_font_size_pt - 1, layout.default_font_size_pt + 2)
    heading_h3 = max(layout.heading_font_size_pt - 3, layout.default_font_size_pt + 1)
    config_font_size = max(layout.code_font_size_pt, layout.default_font_size_pt - 1)
    return f"""
        body {{ font-family: "Segoe UI", Arial, sans-serif; color: #111; }}
        article.document {{ font-size: {layout.default_font_size_pt:.1f}pt; line-height: 1.42; }}
        header {{ margin-bottom: 14pt; border-bottom: 1px solid #d7d7d7; }}
        .doc-name {{ font-size: 9pt; color: #666; padding-bottom: 6pt; }}
        h1, h2, h3, h4, h5, h6 {{ margin: 12pt 0 6pt; font-weight: bold; }}
        h1 {{ font-size: {heading_h1:.1f}pt; }}
        h2 {{ font-size: {heading_h2:.1f}pt; }}
        h3 {{ font-size: {heading_h3:.1f}pt; }}
        p {{ margin: 0 0 7pt; }}
        ul, ol {{ margin: 0 0 8pt 18pt; }}
        li {{ margin-bottom: 2pt; }}
        pre, code {{ font-family: "Consolas", "Courier New", monospace; }}
        pre {{ background: #f5f5f5; border: 1px solid #dfdfdf; padding: 8pt; white-space: pre-wrap; }}
        code, pre {{ font-size: {layout.code_font_size_pt:.1f}pt; }}
        table {{ width: 100%; border-collapse: collapse; margin: 8pt 0; }}
        th, td {{ border: 1px solid #cfcfcf; padding: 4pt 6pt; vertical-align: top; }}
        th {{ background: #ededed; font-weight: bold; }}
        .config {{ font-size: {config_font_size:.1f}pt; line-height: 1.35; }}
    """


def _resolve_kind(ext: str) -> DocumentKind:
    if ext in MARKDOWN_EXTS:
        return DocumentKind.MARKDOWN
    if ext in CONFIG_EXTS:
        return DocumentKind.CONFIG
    return DocumentKind.TEXT


def _build_body_html(kind: DocumentKind, text: str) -> str:
    if kind is DocumentKind.MARKDOWN:
        return render_markdown_html(text)
    if kind is DocumentKind.CONFIG:
        return f"<pre class=\"config\">{html.escape(text)}</pre>"
    return _plain_text_to_html(text)


def _plain_text_to_html(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return "<p></p>"
    return "".join(f"<p>{html.escape(paragraph).replace(chr(10), '<br/>')}</p>" for paragraph in paragraphs)
