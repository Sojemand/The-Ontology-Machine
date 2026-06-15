"""Workflow surface for the built-in PDF extractor."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from .adapter import ensure_pymupdf, read_document
from .block_domain import build_page_blocks
from .policy import record_page_observation, summarize_metadata
from .types import PdfCounters, PdfStageError

_VERSION = "3.0.0"


def extract(input_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    del config
    start = time.perf_counter_ns()
    try:
        document = read_document(Path(input_path))
        counters = PdfCounters()
        blocks: list[dict[str, Any]] = []
        for page in document.pages:
            page_blocks, text_block_count, table_cell_count = build_page_blocks(page)
            blocks.extend(page_blocks)
            record_page_observation(
                counters,
                page_text=page.text,
                has_images=page.has_images,
                text_block_count=text_block_count,
                table_cell_count=table_cell_count,
            )
        metadata = summarize_metadata(document, counters).to_dict()
        return _success_envelope(blocks=blocks, metadata=metadata, needs_ocr=bool(metadata["is_scanned"]), start=start)
    except PdfStageError as exc:
        return _error_envelope(start, str(exc))
    except Exception as exc:
        return _error_envelope(start, f"workflow.extract: {exc}")


def selftest() -> dict[str, Any]:
    try:
        ensure_pymupdf()
    except PdfStageError as exc:
        return {"status": "error", "version": _VERSION, "error": exc.detail}
    return {"status": "ok", "version": _VERSION}


def _success_envelope(
    *,
    blocks: list[dict[str, Any]],
    metadata: dict[str, Any],
    needs_ocr: bool,
    start: int,
) -> dict[str, Any]:
    return {
        "status": "success",
        "blocks": blocks,
        "metadata": metadata,
        "errors": [],
        "needs_ocr": needs_ocr,
        "processing_time_ms": _elapsed_ms(start),
    }


def _error_envelope(start: int, error: str) -> dict[str, Any]:
    return {
        "status": "error",
        "blocks": [],
        "metadata": {},
        "errors": [error],
        "processing_time_ms": _elapsed_ms(start),
        "needs_ocr": False,
    }


def _elapsed_ms(start: int) -> int:
    return (time.perf_counter_ns() - start) // 1_000_000
