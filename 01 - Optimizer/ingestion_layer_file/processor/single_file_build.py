"""Build helpers for explicit single-file processor targets."""
from __future__ import annotations

from pathlib import Path
import uuid

from ..input_catalog import CatalogEntry
from ..models import FileFormat, PluginError, RawExtract, UnsupportedFormatError
from . import validation
from .domain import BuildExtractRequest
from .mail_compound import build_mail_compound_assets
from .single_file_rendering import render_document_assets


def build_single_extract(
    processor,
    entry: CatalogEntry,
    *,
    raw_output_path: Path,
    page_images_dir: Path,
    logical_source_path: str,
) -> tuple[RawExtract, list[str]]:
    file_path = entry.path
    validation.ensure_file_size(entry.size_bytes, processor._config.max_file_size_mb)
    ext = entry.extension.lower() or file_path.suffix.lower()
    fmt = FileFormat.from_ext(ext)
    if fmt == FileFormat.UNKNOWN:
        raise UnsupportedFormatError(f"Kein Plugin fuer Format: {ext}")
    plugin_name = validation.ensure_plugin_name(processor._plugin_mgr.get_plugin_for_format(ext), ext)
    try:
        result = processor._plugin_mgr.invoke(plugin_name, file_path)
    except Exception as exc:
        raise PluginError(plugin_name, str(exc)) from exc
    validation.ensure_success_result(plugin_name, result)
    if getattr(result, "needs_ocr", False):
        raise PluginError(plugin_name, "Plugin meldet OCR-Bedarf, aber kein OCR-Plugin ist konfiguriert")
    content_hash = processor._resolve_content_hash(file_path, entry.content_hash)
    if FileFormat.is_mail_format(fmt):
        compound = build_mail_compound_assets(
            processor,
            file_path,
            fmt=fmt,
            plugin_result=result,
            content_hash=content_hash,
            page_images_dir=page_images_dir,
        )
        source_blocks = compound.source_blocks
        image_paths = compound.image_paths
        plugin_metadata = compound.plugin_metadata
    else:
        source_blocks = processor._parse_blocks(result.blocks)
        image_paths, source_blocks, _, _ = render_document_assets(
            processor,
            file_path,
            fmt=fmt,
            source_blocks=source_blocks,
            page_images_dir=page_images_dir,
        )
        plugin_metadata = dict(result.metadata)
    manifest = processor._plugin_mgr.get_manifest(plugin_name)
    request = BuildExtractRequest(
        file_path=file_path,
        filename=file_path.name,
        relative_path=entry.relative_path,
        size=entry.size_bytes,
        fmt=fmt,
        plugin_name=plugin_name,
        plugin_version=manifest.version if manifest else "",
        processing_time_ms=result.processing_time_ms,
        plugin_metadata=plugin_metadata,
        content_hash=content_hash,
        ingest_id=str(uuid.uuid4()),
        source_blocks=source_blocks,
        image_paths=image_paths,
        page_count=len(image_paths),
        created=entry.created,
        modified=entry.modified,
        source_path_text=logical_source_path,
        source_filename=Path(logical_source_path).name,
        source_relative_path=logical_source_path,
    )
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    extract = processor._build_extract(request)
    return extract, image_paths


def single_entry(file_path: Path) -> CatalogEntry:
    try:
        resolved_path = file_path.resolve()
    except OSError:
        resolved_path = file_path
    stat_result = file_path.stat()
    return CatalogEntry(
        path=resolved_path,
        filename=file_path.name,
        extension=file_path.suffix.lower(),
        size_bytes=stat_result.st_size,
        created="",
        modified="",
        relative_path=file_path.name,
        content_hash="",
    )
