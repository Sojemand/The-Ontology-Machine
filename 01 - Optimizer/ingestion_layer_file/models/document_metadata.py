"""Metadata dataclasses for file optimizer extracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .document_formats import FileFormat


@dataclass
class SourceInfo:
    ingest_id: str = ""
    owner_id: str | None = None
    path: str = ""
    filename: str = ""
    format: str = FileFormat.UNKNOWN
    file_ext: str = ""
    document_type: str | None = None
    language: str | None = None
    size_bytes: int = 0
    created: str = ""
    modified: str = ""
    content_hash: str = ""
    relative_path: str = ""


@dataclass
class ContextInfo:
    page_number: int | None = None
    document_page_count: int | None = None
    source_document_path: str = ""
    page_source_path: str = ""
    interpreter_profile: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionInfo:
    plugin_name: str = ""
    plugin_version: str = ""
    processing_time_ms: int = 0
    block_count: int = 0
    ocr_used: bool = False
