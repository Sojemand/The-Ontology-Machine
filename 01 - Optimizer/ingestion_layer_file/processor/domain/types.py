"""Typed carriers passed from workflow into the processor domain."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import DataBlock


@dataclass(frozen=True)
class BuildExtractRequest:
    file_path: Path
    filename: str
    relative_path: str
    size: int
    fmt: str
    plugin_name: str
    plugin_version: str
    processing_time_ms: int
    plugin_metadata: dict[str, object]
    content_hash: str
    ingest_id: str
    source_blocks: list[DataBlock]
    image_paths: list[str]
    page_count: int
    created: str
    modified: str
    source_path_text: str | None = None
    source_filename: str | None = None
    source_relative_path: str | None = None
