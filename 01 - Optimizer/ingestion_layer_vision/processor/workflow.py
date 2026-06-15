"""Batch-oriented processor workflow stages."""
from __future__ import annotations

import logging
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from ..input_catalog import CatalogEntry
from ..models import PluginError
from . import single_file_workflow, validation
from .source_workflow import _extract_source, _prepare_source
from .types import OutputArtifacts

logger = logging.getLogger(__name__)

_CALLBACK_INTERVAL = 1


def process(processor):
    validation.validate_batch_context(processor)
    try:
        processor._prepare_output_dir(processor._requested_output_dir)
        processor._extracts_dir = processor._output_dir / "raw_extracts"
        processor._extracts_dir.mkdir(parents=True, exist_ok=True)
        processor._start_time = time.perf_counter()
        processor._report.input_after_filter = processor._input_catalog.count_after_filter(processor._filters)
        runner = processor._process_parallel if processor._config.parallel_workers > 1 else processor._process_sequential
        runner(processor._config.parallel_workers)
        processor._update_timing()
        processor._write_report()
        processor._emit_callback()
        return processor._report
    finally:
        processor._shutdown_workers_safe()
        processor._release_output_claim()


def process_sequential(processor, _max_workers: int = 1):
    for entry in processor._input_catalog.iter_filtered(processor._filters, processor._config.processing_order):
        if processor._cancel.is_set():
            break
        processor._process_file(entry)
        if processor._report.total_files_processed % _CALLBACK_INTERVAL == 0:
            processor._update_timing()
            processor._emit_callback()


def process_parallel(processor, max_workers: int):
    entries = iter(processor._input_catalog.iter_filtered(processor._filters, processor._config.processing_order))
    logger.info("Parallele Verarbeitung mit %s Workern und begrenzter Queue", max_workers)
    callback_counter = 0
    max_pending = max(max_workers * 2, max_workers)
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ingest") as executor:
        futures = {}

        def _submit_next() -> bool:
            if processor._cancel.is_set():
                return False
            try:
                entry = next(entries)
            except StopIteration:
                return False
            futures[executor.submit(processor._process_file, entry)] = entry
            return True

        for _ in range(max_pending):
            if not _submit_next():
                break

        while futures:
            done, _pending = wait(futures, return_when=FIRST_COMPLETED)
            if processor._cancel.is_set():
                for pending in futures:
                    pending.cancel()
                break
            for future in done:
                entry = futures.pop(future)
                try:
                    future.result()
                except Exception as exc:
                    logger.warning("Worker-Fehler fuer %s: %s", entry.filename, exc)
                    processor._record_error(entry.filename, "-", f"Unerwarteter Worker-Fehler: {exc}")
                callback_counter += 1
                if callback_counter % _CALLBACK_INTERVAL == 0:
                    processor._update_timing()
                    processor._emit_callback()
                _submit_next()


def process_file(processor, entry: CatalogEntry):
    if processor._cancel.is_set():
        return
    with processor._report_lock:
        processor._report.total_files_processed += 1
        processor._report.current_file = entry.filename
    try:
        source = _prepare_source(processor, entry)
    except Exception as exc:
        processor._record_error(entry.filename, "-", str(exc))
        return

    def _set_current_plugin(name: str) -> None:
        with processor._report_lock:
            processor._report.current_plugin = name

    _set_current_plugin(source.plugin_name)
    artifacts = OutputArtifacts()
    try:
        _extract_source(processor, source, on_plugin_selected=_set_current_plugin)
        asset_key = processor._build_asset_key(source.relative_path, source.content_hash)
        if source.vision:
            artifacts.asset_dirs.append(processor._output_dir / "page_assets" / asset_key)
            artifacts.image_paths = processor._render_vision_assets(
                source.file_path,
                processor._output_dir,
                asset_key,
                render_config=source.render_config,
            )
        source.result, source.plugin_name, source.ocr_was_used = processor._apply_ocr_route(
            file_path=source.file_path,
            filename=source.filename,
            ext=source.ext,
            plugin_name=source.plugin_name,
            result=source.result,
            scan_detected=source.scan_detected,
            vision=source.vision,
            on_plugin_selected=_set_current_plugin,
            image_paths=artifacts.image_paths,
            requires_ocr=source.ocr_required,
            wants_backup_ocr=source.backup_ocr_requested,
        )
        artifacts.blocks = processor._parse_blocks(source.result.blocks)
        extract = processor._build_extract(
            entry=source.entry,
            file_path=source.file_path,
            filename=source.filename,
            ext=source.ext,
            fmt=source.fmt,
            relative_path=source.relative_path,
            size=source.size,
            result=source.result,
            plugin_name=source.plugin_name,
            blocks=artifacts.blocks,
            vision=source.vision,
            scan_detected=source.scan_detected,
            ocr_was_used=source.ocr_was_used,
            image_paths=artifacts.image_paths,
            content_hash=source.content_hash,
            ingest_id=source.ingest_id,
        )
        written_extracts = [extract]
        if source.vision:
            written_extracts.extend(single_file_workflow._build_page_extracts(extract, source.relative_path))
        for item in written_extracts:
            artifacts.written_extract_paths.append(processor._write_extract(item, processor._extracts_dir))
        _record_successful_extracts(processor, source, artifacts, len(written_extracts))
    except PluginError as exc:
        _cleanup_after_failure(processor, source, artifacts)
        processor._record_error(source.filename, exc.plugin_name, str(exc))
        return
    except OSError as exc:
        _cleanup_after_failure(processor, source, artifacts)
        processor._record_error(source.filename, source.plugin_name, f"Output schreiben fehlgeschlagen: {exc}")
        return
    except Exception as exc:
        _cleanup_after_failure(processor, source, artifacts)
        logger.exception("Unerwarteter Verarbeitungsfehler fuer %s", source.filename)
        processor._record_error(source.filename, source.plugin_name, f"Unerwarteter Verarbeitungsfehler: {exc}")
        return

    if processor._input_catalog:
        processor._input_catalog.mark_processed_hash(source.content_hash)
    with processor._report_lock:
        processor._report.successful += 1


def _cleanup_after_failure(processor, source, artifacts: OutputArtifacts) -> None:
    processor._cleanup_generated_output(
        output_dir=processor._output_dir,
        raw_paths=artifacts.written_extract_paths,
        image_paths=artifacts.image_paths,
        asset_dirs=artifacts.asset_dirs,
        ingest_id=source.ingest_id,
    )


def _record_successful_extracts(processor, source, artifacts: OutputArtifacts, written_count: int) -> None:
    with processor._report_lock:
        processor._report.total_extracts_written += written_count
        processor._report.total_blocks_generated += len(artifacts.blocks)
        processor._report.total_images_rendered += len(artifacts.image_paths)
        processor._report.by_format[source.fmt] = processor._report.by_format.get(source.fmt, 0) + written_count
        processor._report.by_plugin[source.plugin_name] = processor._report.by_plugin.get(source.plugin_name, 0) + written_count
        if source.vision:
            processor._report.vision_docs += 1
        else:
            processor._report.text_docs += 1
