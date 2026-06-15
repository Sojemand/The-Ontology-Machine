"""Runtime-facing types, config model, report model and display helpers."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .validation import _coerce_config_int, _normalize_processing_order

logger = logging.getLogger(__name__)


def human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.0f} {unit}" if unit == "B" else f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


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
        if self.max_size_mb is not None:
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IngestionConfig":
        if not isinstance(data, dict):
            logger.warning("Config payload ist kein Mapping, verwende Defaults")
            return cls()
        defaults = cls()
        return cls(
            max_file_size_mb=_coerce_config_int(
                data.get("max_file_size_mb"),
                defaults.max_file_size_mb,
                field_name="max_file_size_mb",
                minimum=0,
            ),
            max_blocks_per_file=_coerce_config_int(
                data.get("max_blocks_per_file"),
                defaults.max_blocks_per_file,
                field_name="max_blocks_per_file",
                minimum=0,
            ),
            max_cell_text_length=_coerce_config_int(
                data.get("max_cell_text_length"),
                defaults.max_cell_text_length,
                field_name="max_cell_text_length",
                minimum=0,
            ),
            processing_order=_normalize_processing_order(
                data.get("processing_order"),
                defaults.processing_order,
            ),
            plugin_timeout_seconds=_coerce_config_int(
                data.get("plugin_timeout_seconds"),
                defaults.plugin_timeout_seconds,
                field_name="plugin_timeout_seconds",
                minimum=1,
            ),
            parallel_workers=_coerce_config_int(
                data.get("parallel_workers"),
                defaults.parallel_workers,
                field_name="parallel_workers",
                minimum=1,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_file_size_mb": self.max_file_size_mb,
            "max_blocks_per_file": self.max_blocks_per_file,
            "max_cell_text_length": self.max_cell_text_length,
            "processing_order": self.processing_order,
            "plugin_timeout_seconds": self.plugin_timeout_seconds,
            "parallel_workers": self.parallel_workers,
        }


class IngestorError(Exception):
    """Basis fuer alle Ingestor-Fehler."""


class PluginError(IngestorError):
    def __init__(self, plugin_name: str, detail: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}': {detail}")


class UnsupportedFormatError(IngestorError):
    pass


class FileTooLargeError(IngestorError):
    pass


class InputFileNotFoundError(IngestorError):
    pass
