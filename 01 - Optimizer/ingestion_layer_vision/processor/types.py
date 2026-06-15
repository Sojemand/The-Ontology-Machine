"""Typed carriers passed between processor workflow stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..input_catalog import CatalogEntry


@dataclass
class PreparedSource:
    entry: CatalogEntry
    file_path: Path
    filename: str
    ext: str
    fmt: str
    relative_path: str
    size: int
    content_hash: str
    ingest_id: str
    plugin_name: str
    result: object | None = None
    scan_detected: bool = False
    vision: bool = False
    ocr_was_used: bool = False
    ocr_required: bool = False
    backup_ocr_requested: bool = False
    render_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputArtifacts:
    image_paths: list[str] = field(default_factory=list)
    asset_dirs: list[Path] = field(default_factory=list)
    written_extract_paths: list[Path] = field(default_factory=list)
    blocks: list = field(default_factory=list)
