"""Runtime-facing types, config model and error hierarchy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .document_types import DataBlock


def human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.0f} {unit}" if unit == "B" else f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@dataclass
class RenderPlanResult:
    blocks: list[DataBlock] = field(default_factory=list)
    page_count: int = 0
    image_paths: list[str] = field(default_factory=list)
    intermediate_pdf_path: str | None = None
    render_route: str = ""
    pagination_source: str = ""


@dataclass
class OutputFilters:
    format: str | None = None
    doc_type: str | None = None
    max_size_mb: int | None = None
    batch_size: int = 0

    def __post_init__(self) -> None:
        self.format = self.format or None
        self.doc_type = self.doc_type or None
        try:
            self.batch_size = int(self.batch_size)
        except (TypeError, ValueError):
            self.batch_size = 0
        if self.batch_size < 0:
            self.batch_size = 0
        if self.max_size_mb is None:
            return
        try:
            self.max_size_mb = int(self.max_size_mb)
        except (TypeError, ValueError):
            self.max_size_mb = None
        else:
            if self.max_size_mb < 0:
                self.max_size_mb = None


@dataclass
class IngestionReport:
    timestamp: str = ""
    input_directory: str = ""
    output_directory: str = ""
    input_total: int = 0
    input_after_filter: int = 0
    filters_applied: dict[str, Any] = field(default_factory=dict)
    total_files_processed: int = 0
    successful: int = 0
    failed: int = 0
    total_extracts_written: int = 0
    by_format: dict[str, int] = field(default_factory=dict)
    by_plugin: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    vision_docs: int = 0
    text_docs: int = 0
    total_blocks_generated: int = 0
    total_images_rendered: int = 0
    processing_time_seconds: float = 0.0
    avg_time_per_file_ms: float = 0.0
    current_file: str = ""
    current_plugin: str = ""


@dataclass
class IngestionConfig:
    max_file_size_mb: int = 100
    max_blocks_per_file: int = 50000
    max_cell_text_length: int = 8000
    processing_order: str = "input"
    plugin_timeout_seconds: int = 120
    parallel_workers: int = 1
    render_dpi: int = 150
    render_width_px: int = 1240
    render_height_px: int = 1754
    page_margin_pt: int = 54
    default_font_size_pt: int = 10
    code_font_size_pt: int = 9
    heading_font_size_pt: int = 16

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IngestionConfig":
        from .config import parse_ingestion_config

        return parse_ingestion_config(data)


class IngestorError(Exception):
    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class UnsupportedFormatError(IngestorError):
    pass


class PluginError(IngestorError):
    def __init__(self, plugin_name: str, message: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}': {message}")


class FileTooLargeError(IngestorError):
    pass


class InputFileNotFoundError(IngestorError):
    pass
