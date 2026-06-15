"""Thin public surface and report/debug helpers for the processor."""
from __future__ import annotations

import copy
import logging
import threading
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..input_catalog import InputCatalog
from ..models import IngestionConfig, IngestionReport, OutputFilters
from ..plugin_manager import PluginManager
from . import (
    adapter,
    claims_repository,
    cleanup_repository,
    domain,
    extracts_repository,
    hashing_repository,
    policy,
    report_repository,
    single_file_workflow,
    validation,
    workflow,
)

logger = logging.getLogger(__name__)


def record_error(processor, filename: str, plugin: str, error: str):
    with processor._report_lock:
        processor._report.failed += 1
        if len(processor._report.errors) < 1000:
            processor._report.errors.append({"file": filename, "plugin": plugin, "error": error, "timestamp": datetime.now().isoformat()})
    logger.warning("Verarbeitung fehlgeschlagen: %s (%s)", filename, error)


def update_timing(processor):
    elapsed = time.perf_counter() - processor._start_time
    with processor._report_lock:
        processor._report.processing_time_seconds = round(elapsed, 1)
        if processor._report.total_files_processed > 0:
            processor._report.avg_time_per_file_ms = int(round((elapsed * 1000) / processor._report.total_files_processed))


def snapshot_report(processor) -> IngestionReport:
    with processor._report_lock:
        return copy.deepcopy(processor._report)


def emit_callback(processor) -> None:
    if not processor._callback:
        return
    try:
        processor._callback(processor._snapshot_report())
    except Exception:
        logger.exception("Progress-Callback fehlgeschlagen")


def shutdown_workers_safe(processor) -> None:
    try:
        processor._plugin_mgr.shutdown_workers()
    except Exception:
        logger.exception("shutdown_workers() fehlgeschlagen")


def rollback_extract_report(processor, *, written_extract_count: int, block_count: int, image_count: int, fmt: str, plugin_name: str, vision: bool) -> None:
    if written_extract_count <= 0:
        return
    with processor._report_lock:
        processor._report.total_extracts_written = max(0, processor._report.total_extracts_written - written_extract_count)
        processor._report.total_blocks_generated = max(0, processor._report.total_blocks_generated - block_count)
        processor._report.total_images_rendered = max(0, processor._report.total_images_rendered - image_count)
        next_format = processor._report.by_format.get(fmt, 0) - written_extract_count
        next_plugin = processor._report.by_plugin.get(plugin_name, 0) - written_extract_count
        if next_format > 0:
            processor._report.by_format[fmt] = next_format
        else:
            processor._report.by_format.pop(fmt, None)
        if next_plugin > 0:
            processor._report.by_plugin[plugin_name] = next_plugin
        else:
            processor._report.by_plugin.pop(plugin_name, None)
        target = "vision_docs" if vision else "text_docs"
        setattr(processor._report, target, max(0, getattr(processor._report, target) - written_extract_count))


def cancel(processor) -> None:
    processor._cancel.set()
    processor._plugin_mgr.kill_all()


class Processor:
    def __init__(
        self,
        config: IngestionConfig,
        plugin_mgr: PluginManager,
        input_catalog: InputCatalog | None = None,
        filters: OutputFilters | None = None,
        output_dir: Path | None = None,
        callback: Callable[[IngestionReport], None] | None = None,
        runtime_policy_state=None,
    ):
        self._config = config
        self._plugin_mgr = plugin_mgr
        self._input_catalog = input_catalog
        self._filters = filters or OutputFilters()
        self._requested_output_dir = Path(output_dir) if output_dir else None
        self._output_dir = self._requested_output_dir
        self._callback = callback
        self._runtime_policy_state = runtime_policy_state
        self._cancel = threading.Event()
        self._report_lock = threading.Lock()
        self._extracts_dir = (self._output_dir / "raw_extracts") if self._output_dir else None
        self._run_lock_path: Path | None = None
        self._start_time = 0.0
        self._report = IngestionReport(
            timestamp=datetime.now().isoformat(),
            input_directory=str(input_catalog.path) if input_catalog and input_catalog.path else "",
            output_directory=str(self._output_dir) if self._output_dir else "",
            input_total=input_catalog.total_count if input_catalog else 0,
            filters_applied=asdict(self._filters),
        )

    process = workflow.process
    process_single = single_file_workflow.process_single
    cancel = cancel
    _process_sequential = workflow.process_sequential
    _process_parallel = workflow.process_parallel
    _process_file = workflow.process_file
    _invoke_plugin = adapter.invoke_plugin
    _detect_scan_state = adapter.detect_scan_state
    _is_ocr_plugin = adapter.is_ocr_plugin
    _resolve_ocr_plugin_name = adapter.resolve_ocr_plugin_name
    _apply_ocr_route = adapter.apply_ocr_route
    _build_extract = domain.build_extract
    _parse_blocks = domain.parse_blocks
    _prepare_output_dir = claims_repository.prepare_output_dir
    _set_output_dir = claims_repository.set_output_dir
    _try_claim_output_dir = claims_repository.try_claim_output_dir
    _claim_child_output_dir = claims_repository.claim_child_output_dir
    _release_output_claim = claims_repository.release_output_claim
    _write_extract = extracts_repository.write_extract
    _write_extract_to_path = extracts_repository.write_extract_to_path
    _build_and_write_extract = extracts_repository.build_and_write_extract
    _cleanup_generated_output = cleanup_repository.cleanup_generated_output
    _render_vision_assets = adapter.render_vision_assets
    _try_claim_output_candidate = claims_repository.try_claim_output_candidate
    _write_report = report_repository.write_report
    _record_error = record_error
    _update_timing = update_timing
    _snapshot_report = snapshot_report
    _emit_callback = emit_callback
    _shutdown_workers_safe = shutdown_workers_safe
    _rollback_extract_report = rollback_extract_report
    _normalize_content_hash = staticmethod(validation.normalize_content_hash)
    _resolve_content_hash = validation.resolve_content_hash
    _archive_dir_name = staticmethod(validation.archive_dir_name)
    _require_vision_output_dir = staticmethod(validation.require_vision_output_dir)
    _result_error_detail = staticmethod(validation.result_error_detail)
    _normalize_output_seed = staticmethod(policy.normalize_output_seed)
    _sanitize_output_fragment = staticmethod(policy.sanitize_output_fragment)
    _build_asset_key = staticmethod(policy.build_asset_key)
    _build_output_slug = staticmethod(policy.build_output_slug)
    _short_output_token = staticmethod(policy.short_output_token)
    _iter_output_candidates = staticmethod(policy.iter_output_candidates)
    _output_claim_path = staticmethod(claims_repository.output_claim_path)
    _compute_hash = staticmethod(hashing_repository.compute_hash)
