"""Soft heuristics for PDF scan and density metadata."""
from __future__ import annotations

from .types import PdfCounters, PdfDocumentSnapshot, PdfMetadataSummary

_SCAN_CHAR_THRESHOLD = 50


def record_page_observation(
    counters: PdfCounters,
    *,
    page_text: str,
    has_images: bool,
    text_block_count: int,
    table_cell_count: int,
) -> None:
    page_chars = len(page_text.strip())
    counters.total_chars += page_chars
    counters.text_block_count += text_block_count
    counters.table_cell_count += table_cell_count
    if page_chars < _SCAN_CHAR_THRESHOLD:
        counters.scan_pages += 1
    if has_images:
        counters.has_images = True


def summarize_metadata(document: PdfDocumentSnapshot, counters: PdfCounters) -> PdfMetadataSummary:
    page_count = document.page_count
    is_scanned = counters.scan_pages == page_count and page_count > 0
    chars_per_page = counters.total_chars / page_count if page_count > 0 else 0.0
    return PdfMetadataSummary(
        page_count=page_count,
        is_scanned=is_scanned,
        has_images=counters.has_images or is_scanned,
        text_density=_text_density_label(chars_per_page),
        avg_chars_per_page=chars_per_page,
        text_block_count=counters.text_block_count,
        table_cell_count=counters.table_cell_count,
        pdf_version=document.pdf_version,
        has_annotations=document.has_annotations,
    )


def _text_density_label(chars_per_page: float) -> str:
    if chars_per_page < 200:
        return "sparse"
    if chars_per_page < 1000:
        return "medium"
    return "dense"
