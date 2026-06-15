"""Minimal raw-v2 serialization for the optimizer file profile."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .document_blocks import BlockFormatting, BlockPosition, DataBlock
from .document_metadata import ContextInfo, ExtractionInfo, SourceInfo
from .document_raw import RawExtract
from .repository import atomic_json_write
from .validation import _validate_raw_extract_consistency

RAW_SCHEMA_VERSION = "optimizer_raw_v2"


def raw_extract_to_dict(extract: RawExtract) -> dict[str, object]:
    _validate_raw_extract_consistency(extract)
    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "optimizer_profile": "file",
        "source": _compact_mapping(_serialize_source(extract.source, extract.total_pages)),
        "extraction": _compact_mapping(_serialize_extraction(extract.extraction)),
        "metadata": _compact_mapping(dict(extract.metadata)),
        "context": _compact_mapping(_serialize_context(extract.context, extract.page_number, extract.total_pages)),
        "ocr_reference": {
            "blocks": [_serialize_block(block) for block in extract.blocks],
        },
    }


def write_raw_extract(path: Path, extract: RawExtract) -> None:
    atomic_json_write(path, raw_extract_to_dict(extract))


def _serialize_source(source: SourceInfo, page_count: int | None) -> dict[str, Any]:
    file_ext = (source.file_ext or "").strip()
    if not file_ext:
        file_ext = Path(source.path or source.filename).suffix.lower()
    return {
        "ingest_id": source.ingest_id or None,
        "file_name": source.filename or None,
        "file_path": source.path or None,
        "relative_path": source.relative_path or None,
        "file_ext": file_ext or None,
        "content_hash": source.content_hash or None,
        "page_count": page_count,
        "document_type": source.document_type or None,
        "language": source.language or None,
        "size_bytes": source.size_bytes,
        "created_at": source.created or None,
        "modified_at": source.modified or None,
    }


def _serialize_extraction(extraction: ExtractionInfo) -> dict[str, Any]:
    return {
        "plugin_name": extraction.plugin_name or None,
        "plugin_version": extraction.plugin_version or None,
        "processing_time_ms": extraction.processing_time_ms,
    }


def _serialize_context(
    context: ContextInfo,
    page_number: int | None,
    document_page_count: int | None,
) -> dict[str, Any]:
    return {
        "page_number": page_number if page_number is not None else context.page_number,
        "document_page_count": (
            document_page_count if document_page_count is not None else context.document_page_count
        ),
        "source_document_path": context.source_document_path or None,
        "page_source_path": context.page_source_path or None,
        "interpreter_profile": context.interpreter_profile or None,
    }


def _serialize_block(block: DataBlock) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": block.id,
        "type": block.type,
        "value": _serialize_value(block.value),
    }
    if block.value_type and block.value_type != "text":
        payload["value_type"] = block.value_type
    position = _serialize_position(block.position)
    if position:
        payload["position"] = position
    formatting = _serialize_formatting(block.formatting)
    if formatting:
        payload["formatting"] = formatting
    if block.page_span:
        payload["page_span"] = [int(item) for item in block.page_span if item is not None]
    origin = _compact_mapping(dict(block.origin or {}))
    if origin:
        payload["origin"] = origin
    return payload


def _serialize_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _serialize_position(position: BlockPosition) -> dict[str, Any]:
    return _compact_mapping(
        {
            "sheet": position.sheet,
            "row": position.row,
            "col": position.col,
            "page": position.page,
            "paragraph_index": position.paragraph_index,
            "table_index": position.table_index,
        }
    )


def _serialize_formatting(formatting: BlockFormatting | None) -> dict[str, Any]:
    if formatting is None:
        return {}
    if formatting.bold is True:
        return {"bold": True}
    return {}


def _compact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in data.items():
        normalized = _compact_value(value)
        if normalized in (None, "", [], {}):
            continue
        compacted[str(key)] = normalized
    return compacted


def _compact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _compact_mapping(value)
    if isinstance(value, list):
        items = [_compact_value(item) for item in value]
        return [item for item in items if item not in (None, "", [], {})]
    return value
