"""Workflow surface for the built-in markdown/text extractor."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .config_domain import parse_config
from .markdown_domain import parse_markdown
from .text_domain import parse_plaintext

_MARKDOWN_EXTS = {".md", ".markdown"}
_CONFIG_EXTS = {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties"}


def extract(input_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    del config
    start = time.perf_counter_ns()
    path = Path(input_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "status": "error",
            "blocks": [],
            "metadata": {},
            "errors": [str(exc)],
            "processing_time_ms": 0,
            "needs_ocr": False,
        }

    ext = path.suffix.lower()
    is_markdown = ext in _MARKDOWN_EXTS
    if is_markdown:
        outcome = parse_markdown(text.split("\n"))
    elif ext in _CONFIG_EXTS:
        outcome = parse_config(text.split("\n"), ext)
    else:
        outcome = parse_plaintext(text)

    metadata = {
        "word_count": len(text.split()),
        "line_count": len(text.split("\n")),
        "heading_count": outcome.metrics.heading_count,
        "headings": outcome.metrics.heading_summary() or None,
        "has_code_blocks": outcome.metrics.code_block_count > 0,
        "code_block_count": outcome.metrics.code_block_count,
        "list_item_count": outcome.metrics.list_item_count,
        "is_markdown": is_markdown,
    }
    return {
        "status": "success",
        "blocks": outcome.blocks,
        "metadata": metadata,
        "errors": [],
        "processing_time_ms": (time.perf_counter_ns() - start) // 1_000_000,
        "needs_ocr": False,
    }
