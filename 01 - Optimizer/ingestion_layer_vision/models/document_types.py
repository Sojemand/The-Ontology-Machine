"""Document-facing types for the Optimizer raw pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class FileFormat:
    MSG = "msg"
    XLSX = "xlsx"
    XLS = "xls"
    XLSB = "xlsb"
    XLSM = "xlsm"
    ODS = "ods"
    DOCX = "docx"
    DOC = "doc"
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    CAD = "cad"
    ZIP = "zip"
    UNKNOWN = "unknown"

    ALL = [PDF, IMAGE, TEXT, UNKNOWN]
    EXT_MAP: dict[str, str] = {
        ".pdf": PDF,
        ".jpg": IMAGE,
        ".jpeg": IMAGE,
        ".png": IMAGE,
        ".tif": IMAGE,
        ".tiff": IMAGE,
        ".bmp": IMAGE,
        ".webp": IMAGE,
        ".md": TEXT,
        ".markdown": TEXT,
        ".txt": TEXT,
        ".text": TEXT,
        ".rst": TEXT,
        ".yaml": TEXT,
        ".yml": TEXT,
        ".toml": TEXT,
        ".ini": TEXT,
        ".log": TEXT,
        ".tex": TEXT,
        ".cfg": TEXT,
        ".conf": TEXT,
        ".env": TEXT,
        ".properties": TEXT,
    }

    @staticmethod
    def from_ext(ext: str) -> str:
        return FileFormat.EXT_MAP.get(ext.lower(), FileFormat.UNKNOWN)


class ValueType:
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    FORMULA = "formula"
    BOOLEAN = "boolean"
    EMPTY = "empty"
    CURRENCY = "currency"


class BlockType:
    CELL = "cell"
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"
    HEADER = "header"
    EMAIL_FIELD = "email_field"
    METADATA = "metadata"
    CHAT_MESSAGE = "chat_message"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"


@dataclass
class BlockPosition:
    sheet: str | None = None
    row: int | None = None
    col: int | None = None
    col_letter: str | None = None
    page: int | None = None
    paragraph_index: int | None = None
    table_index: int | None = None


@dataclass
class BlockFormatting:
    bold: bool | None = None
    font_size: float | None = None
    merged_with: list[str] | None = None


@dataclass
class DataBlock:
    id: str
    type: str
    position: BlockPosition
    value: Any = None
    value_type: str = ValueType.TEXT
    layout_label: str | None = None
    formatting: BlockFormatting | None = None
    confidence: float | None = None


@dataclass
class SourceInfo:
    ingest_id: str = ""
    owner_id: str | None = None
    path: str = ""
    filename: str = ""
    file_ext: str = ""
    format: str = FileFormat.UNKNOWN
    size_bytes: int = 0
    created: str = ""
    modified: str = ""
    content_hash: str = ""
    relative_path: str = ""


@dataclass
class ContextInfo:
    path_segments: list[str] = field(default_factory=list)
    inferred_customer: str | None = None
    inferred_year: str | None = None
    inferred_project: str | None = None


@dataclass
class ExtractionInfo:
    plugin_name: str = ""
    plugin_version: str = ""
    processing_time_ms: int = 0
    block_count: int = 0
    ocr_used: bool = False


@dataclass
class StructuralSignature:
    format: str = FileFormat.UNKNOWN
    row_patterns: list[str] | None = None
    col_types: dict[str, str] | None = None
    header_keywords: list[str] | None = None
    sheet_count: int | None = None
    has_tables: bool | None = None
    table_col_count: list[int] | None = None
    heading_keywords: list[str] | None = None
    paragraph_count: int | None = None
    page_count: int | None = None
    has_images: bool | None = None
    text_density: str | None = None
    keyword_fingerprint: list[str] = field(default_factory=list)


@dataclass
class RawExtract:
    source: SourceInfo = field(default_factory=SourceInfo)
    context: ContextInfo = field(default_factory=ContextInfo)
    extraction: ExtractionInfo = field(default_factory=ExtractionInfo)
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_llm_vision: bool = False
    image_paths: list[str] = field(default_factory=list)
    blocks: list[DataBlock] = field(default_factory=list)
    is_scan: bool = False
    page_number: int | None = None
    total_pages: int | None = None

    def to_dict(self) -> dict[str, Any]:
        from .raw_workflow import raw_extract_to_dict

        return raw_extract_to_dict(self)

