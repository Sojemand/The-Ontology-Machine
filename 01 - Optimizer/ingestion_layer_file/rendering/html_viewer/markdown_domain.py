"""Pure markdown shaping with deterministic fallback rendering."""
from __future__ import annotations

import html
import importlib
import re


def render_markdown_html(text: str) -> str:
    module = _load_markdown_module()
    if module is not None:
        try:
            return module.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
        except Exception:
            pass
    return _fallback_markdown_to_html(text)


def _load_markdown_module():
    try:
        return importlib.import_module("markdown")
    except Exception:
        return None


def _fallback_markdown_to_html(text: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    code_block: list[str] = []
    in_code_block = False
    ordered_list = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{html.escape(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            tag = "ol" if ordered_list else "ul"
            blocks.append(f"<{tag}>{''.join(list_items)}</{tag}>")
            list_items = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code_block:
                blocks.append(f"<pre><code>{html.escape(chr(10).join(code_block))}</code></pre>")
                code_block = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        if in_code_block:
            code_block.append(raw_line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{html.escape(heading.group(2).strip())}</h{level}>")
            continue
        list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", line)
        if list_match:
            flush_paragraph()
            ordered_list = list_match.group(2).endswith(".")
            list_items.append(f"<li>{html.escape(list_match.group(3).strip())}</li>")
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    if code_block:
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_block))}</code></pre>")
    return "".join(blocks) or "<p></p>"
