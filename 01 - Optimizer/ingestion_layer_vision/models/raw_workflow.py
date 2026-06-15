"""Minimal raw serialization for the vision Optimizer contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .document_types import BlockFormatting, DataBlock, RawExtract
from .repository import atomic_json_write
from .validation import _validate_raw_extract_consistency

RAW_SCHEMA_VERSION = "optimizer_raw_v2"


def raw_extract_to_dict(extract: RawExtract) -> dict[str, Any]:
    _validate_raw_extract_consistency(extract)
    metadata = _clean_metadata(extract.metadata)
    context = _drop_empty(_build_context(extract))
    return {
        "schema_version": RAW_SCHEMA_VERSION,
        "optimizer_profile": "vision",
        "source": _drop_empty(_build_source(extract)),
        "extraction": _drop_empty(_build_extraction(extract)),
        "metadata": {} if _should_drop(metadata) else metadata,
        "context": {} if _should_drop(context) else context,
        "ocr_reference": {"blocks": _build_ocr_blocks(extract.blocks)},
    }


def write_raw_extract(path: Path, extract: RawExtract) -> None:
    atomic_json_write(path, raw_extract_to_dict(extract))


def _build_source(extract: RawExtract) -> dict[str, Any]:
    source = extract.source
    metadata = extract.metadata if isinstance(extract.metadata, dict) else {}
    page_count = _first_present(
        extract.total_pages,
        metadata.get("page_count"),
        len(extract.image_paths) if extract.image_paths else None,
        1 if extract.page_number is not None else None,
    )
    return {
        "ingest_id": source.ingest_id,
        "file_name": source.filename,
        "file_path": source.path,
        "relative_path": source.relative_path,
        "file_ext": source.file_ext or Path(source.filename).suffix.lower(),
        "content_hash": source.content_hash,
        "page_count": page_count,
        "document_type": source.format,
        "language": metadata.get("language"),
        "size_bytes": source.size_bytes,
        "created_at": source.created,
        "modified_at": source.modified,
        "is_scan": extract.is_scan,
        "has_handwriting": metadata.get("has_handwriting"),
    }


def _build_extraction(extract: RawExtract) -> dict[str, Any]:
    extraction = extract.extraction
    return {
        "plugin_name": extraction.plugin_name,
        "plugin_version": extraction.plugin_version,
        "processing_time_ms": extraction.processing_time_ms,
        "ocr_used": extraction.ocr_used,
    }


def _build_context(extract: RawExtract) -> dict[str, Any]:
    source_document_path = _source_document_path(extract)
    page_source_path = _page_source_path(extract, source_document_path)
    return {
        "page_number": extract.page_number,
        "document_page_count": extract.total_pages,
        "source_document_path": source_document_path,
        "page_source_path": page_source_path,
    }


def _source_document_path(extract: RawExtract) -> str:
    source_path = extract.source.relative_path or extract.source.path
    marker = "::page="
    if marker in source_path:
        return source_path.split(marker, 1)[0]
    return source_path


def _page_source_path(extract: RawExtract, source_document_path: str) -> str | None:
    if extract.page_number is None:
        return None
    source_path = extract.source.relative_path or extract.source.path
    if "::page=" in source_path:
        return source_path
    total_pages = extract.total_pages or 1
    return f"{source_document_path}::page={extract.page_number:03d}-of-{total_pages:03d}"


def _build_ocr_blocks(blocks: list[DataBlock]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for block in blocks:
        if _is_empty_value(block.value):
            continue
        serialized.append(_drop_empty(_block_to_dict(block)))
    return serialized


def _block_to_dict(block: DataBlock) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": block.id,
        "type": block.type,
        "layout_label": block.layout_label,
        "value": block.value,
        "confidence": block.confidence,
        "formatting": _formatting_to_dict(block.formatting),
    }
    if block.value_type and block.value_type != "text":
        payload["value_type"] = block.value_type
    return payload


def _formatting_to_dict(formatting: BlockFormatting | None) -> dict[str, Any]:
    if formatting is None:
        return {}
    if formatting.bold is True:
        return {"bold": True}
    return {}


def _clean_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            nested = _clean_metadata(item)
            if _should_drop(nested):
                continue
            cleaned[key] = nested
        return cleaned
    if isinstance(value, list):
        cleaned_items = []
        for item in value:
            nested = _clean_metadata(item)
            if not _should_drop(nested):
                cleaned_items.append(nested)
        return cleaned_items
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _drop_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            nested = _drop_empty(item)
            if _should_drop(nested):
                continue
            cleaned[key] = nested
        return cleaned
    if isinstance(value, list):
        cleaned_items = []
        for item in value:
            nested = _drop_empty(item)
            if not _should_drop(nested):
                cleaned_items.append(nested)
        return cleaned_items
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _should_drop(value: Any) -> bool:
    return value is None or isinstance(value, (dict, list)) and not value


def _is_empty_value(value: Any) -> bool:
    return value is None or isinstance(value, str) and not value.strip()


def _first_present(*values: Any) -> Any:
    for value in values:
        if _should_drop(value):
            continue
        return value
    return None
