"""Processing workflow for the optimizer file profile."""
from __future__ import annotations

from pathlib import Path
import sys
import time
import uuid

from ..input_catalog import CatalogEntry
from ..models import FileFormat, PluginError, RawExtract, UnsupportedFormatError
from . import validation
from .domain import BuildExtractRequest
from .mail_compound import build_mail_compound_assets
def _surface_module():
    return sys.modules[__package__]
def process(processor):
    validation.validate_batch_context(processor)
    try:
        processor._prepare_output_dir(processor._requested_output_dir)
        processor._start_time = time.perf_counter()
        processor._report.input_after_filter = processor._input_catalog.count_after_filter(processor._filters)
        for entry in processor._input_catalog.iter_filtered(processor._filters, processor._config.processing_order):
            if processor._cancel.is_set():
                break
            process_file(processor, entry)
            processor._update_timing()
            processor._emit_callback()
        processor._write_report()
        return processor._snapshot_report()
    finally:
        processor._shutdown_workers_safe()
        processor._release_output_claim()
def process_single(processor, file_path: str | Path, write_output: bool = True, output_dir: str | Path | None = None) -> list[RawExtract]:
    if not write_output:
        raise ValueError("Optimizer erfordert write_output=True und ein output_dir")
    target_output = Path(output_dir) if output_dir else processor._requested_output_dir
    if target_output is None:
        raise ValueError("process_single() erfordert ein output_dir")
    source = Path(file_path)
    validation.ensure_existing_file(source)
    try:
        resolved_source = source.resolve()
    except OSError:
        resolved_source = source
    entry = CatalogEntry(
        path=resolved_source,
        filename=source.name,
        extension=source.suffix.lower(),
        size_bytes=source.stat().st_size,
        created="",
        modified="",
        relative_path=source.name,
        content_hash="",
    )
    processor._prepare_output_dir(target_output)
    try:
        return [process_entry(processor, entry)]
    finally:
        processor._release_output_claim()
def process_file(processor, entry: CatalogEntry | dict[str, object]) -> None:
    catalog_entry = _coerce_entry(entry)
    filename = catalog_entry.filename
    with processor._report_lock:
        processor._report.total_files_processed += 1
        processor._report.current_file = filename
    try:
        process_entry(processor, catalog_entry)
    except Exception as exc:
        processor._record_error(filename, str(processor._report.current_plugin or "-"), str(exc))
def process_entry(processor, entry: CatalogEntry | dict[str, object]) -> RawExtract:
    catalog_entry = _coerce_entry(entry)
    file_path = catalog_entry.path
    validation.ensure_existing_file(file_path)
    size = catalog_entry.size_bytes
    validation.ensure_file_size(size, processor._config.max_file_size_mb)
    filename = catalog_entry.filename or file_path.name
    relative_path = catalog_entry.relative_path or filename
    ext = catalog_entry.extension.lower() or file_path.suffix.lower()
    fmt = FileFormat.from_ext(ext)
    if fmt == FileFormat.UNKNOWN:
        raise UnsupportedFormatError(f"Kein Plugin fuer Format: {ext}")
    plugin_name = validation.ensure_plugin_name(processor._plugin_mgr.get_plugin_for_format(ext), ext)
    with processor._report_lock:
        processor._report.current_plugin = plugin_name

    try:
        result = processor._plugin_mgr.invoke(plugin_name, file_path)
    except Exception as exc:
        raise PluginError(plugin_name, str(exc)) from exc
    validation.ensure_success_result(plugin_name, result)
    if getattr(result, "needs_ocr", False):
        raise PluginError(plugin_name, "Plugin meldet OCR-Bedarf, aber kein OCR-Plugin ist konfiguriert")
    content_hash = processor._resolve_content_hash(file_path, catalog_entry.content_hash)
    asset_key = processor._build_asset_key(relative_path, content_hash)
    asset_dir = processor._output_dir / "page_images" / asset_key
    image_paths: list[str] = []
    written_raw: list[Path] = []
    ingest_id = ""
    try:
        if FileFormat.is_mail_format(fmt):
            compound = build_mail_compound_assets(
                processor,
                file_path,
                fmt=fmt,
                plugin_result=result,
                content_hash=content_hash,
                page_images_dir=asset_dir,
            )
            source_blocks = compound.source_blocks
            image_paths = compound.image_paths
            plugin_metadata = compound.plugin_metadata
        else:
            source_blocks = processor._parse_blocks(result.blocks)
            image_paths, source_blocks, _, _ = _surface_module().render_document_assets(
                processor,
                file_path,
                fmt=fmt,
                source_blocks=source_blocks,
                page_images_dir=asset_dir,
            )
            plugin_metadata = dict(result.metadata)
        if not image_paths:
            raise OSError(f"Vision-Assets fehlen fuer {file_path}")
        manifest = processor._plugin_mgr.get_manifest(plugin_name)
        ingest_id = str(uuid.uuid4())
        request = BuildExtractRequest(
            file_path=file_path,
            filename=filename,
            relative_path=relative_path,
            size=size,
            fmt=fmt,
            plugin_name=plugin_name,
            plugin_version=manifest.version if manifest else "",
            processing_time_ms=result.processing_time_ms,
            plugin_metadata=plugin_metadata,
            content_hash=content_hash,
            ingest_id=ingest_id,
            source_blocks=source_blocks,
            image_paths=image_paths,
            page_count=len(image_paths),
            created=catalog_entry.created,
            modified=catalog_entry.modified,
        )
        extract = processor._build_extract(request)
        try:
            raw_path = processor._build_and_write_extract(
                entry=catalog_entry,
                file_path=file_path,
                filename=filename,
                ext=ext,
                fmt=fmt,
                relative_path=relative_path,
                size=size,
                result=result,
                plugin_name=plugin_name,
                blocks=source_blocks,
                vision=True,
                scan_detected=False,
                ocr_was_used=False,
                image_paths=image_paths,
                content_hash=content_hash,
                ingest_id=ingest_id,
                request=request,
                extract=extract,
            )
        except OSError as exc:
            raise OSError(f"Output schreiben fehlgeschlagen: {exc}") from exc
        if raw_path is not None:
            written_raw.append(raw_path)
        processor._mark_success(extract, fmt, plugin_name, content_hash)
        return extract
    except Exception:
        processor._cleanup_generated_output(
            output_dir=processor._output_dir,
            raw_paths=written_raw,
            image_paths=image_paths,
            asset_dirs=[asset_dir],
            ingest_id=ingest_id,
        )
        raise
def _coerce_entry(entry: CatalogEntry | dict[str, object]) -> CatalogEntry:
    if isinstance(entry, CatalogEntry):
        return entry
    file_path = Path(str(entry.get("path", "")))
    try:
        resolved_path = file_path.resolve()
    except OSError:
        resolved_path = file_path
    return CatalogEntry(
        path=resolved_path,
        filename=str(entry.get("filename", file_path.name)),
        extension=str(entry.get("extension", file_path.suffix.lower())).lower(),
        size_bytes=int(entry.get("size_bytes", 0) or 0),
        created=str(entry.get("created", "")),
        modified=str(entry.get("modified", "")),
        relative_path=str(entry.get("relative_path", file_path.name)),
        content_hash=str(entry.get("content_hash", "")),
    )
