"""Reporting helpers for explicit single-file processor targets."""
from __future__ import annotations

from ..models import RawExtract


def record_single_extract(processor, extract: RawExtract, *, image_count: int) -> None:
    with processor._report_lock:
        processor._report.total_extracts_written += 1
        processor._report.total_blocks_generated += len(extract.blocks)
        processor._report.total_images_rendered += image_count
        processor._report.by_format[extract.source.format] = processor._report.by_format.get(extract.source.format, 0) + 1
        plugin_name = extract.extraction.plugin_name
        processor._report.by_plugin[plugin_name] = processor._report.by_plugin.get(plugin_name, 0) + 1
        processor._report.vision_docs += 1
