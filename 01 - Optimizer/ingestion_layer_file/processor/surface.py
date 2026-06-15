"""Thin processor surface and report/debug helpers."""
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
from . import claims_repository, domain, policy, repository, single_file_workflow, validation, workflow

logger = logging.getLogger(__name__)


def record_error(processor, filename: str, plugin: str, error: str) -> None:
    with processor._report_lock:
        processor._report.failed += 1
        processor._report.errors.append({"file": filename, "plugin": plugin, "error": error, "timestamp": datetime.now().isoformat()})
    logger.warning("Verarbeitung fehlgeschlagen: %s (%s)", filename, error)


def update_timing(processor) -> None:
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


def cancel(processor) -> None:
    processor._cancel.set()
    processor._plugin_mgr.kill_all()


def mark_success(processor, extract, fmt: str, plugin_name: str, content_hash: str) -> None:
    del extract, fmt, plugin_name
    with processor._report_lock:
        processor._report.successful += 1
    if processor._input_catalog and content_hash:
        processor._input_catalog.mark_processed_hash(content_hash)


class Processor:
    def __init__(
        self,
        config: IngestionConfig,
        plugin_mgr: PluginManager,
        input_catalog: InputCatalog | None = None,
        filters: OutputFilters | None = None,
        output_dir: Path | None = None,
        callback: Callable[[IngestionReport], None] | None = None,
    ) -> None:
        self._config = config
        self._plugin_mgr = plugin_mgr
        self._input_catalog = input_catalog
        self._filters = filters or OutputFilters()
        self._requested_output_dir = Path(output_dir) if output_dir else None
        self._output_dir = self._requested_output_dir
        self._callback = callback
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
    _process_file = workflow.process_file
    _process_entry = workflow.process_entry
    _build_extract = domain.build_extract
    _parse_blocks = domain.parse_blocks
    _prepare_output_dir = claims_repository.prepare_output_dir
    _set_output_dir = claims_repository.set_output_dir
    _try_claim_output_dir = claims_repository.try_claim_output_dir
    _claim_child_output_dir = claims_repository.claim_child_output_dir
    _release_output_claim = claims_repository.release_output_claim
    _write_claim_token = claims_repository.write_claim_token
    _claim_token_path = claims_repository.claim_token_path
    _output_claim_path = staticmethod(claims_repository.output_claim_path)
    _try_claim_output_candidate = claims_repository.try_claim_output_candidate
    _write_extract = repository.write_extract
    _write_extract_to_path = repository.write_extract_to_path
    _build_and_write_extract = repository.build_and_write_extract
    _cleanup_generated_output = repository.cleanup_generated_output
    _cleanup_outputs = repository.cleanup_outputs
    _write_report = repository.write_report
    _record_error = record_error
    _update_timing = update_timing
    _snapshot_report = snapshot_report
    _emit_callback = emit_callback
    _shutdown_workers_safe = shutdown_workers_safe
    _mark_success = mark_success
    _normalize_content_hash = staticmethod(validation.normalize_content_hash)
    _resolve_content_hash = validation.resolve_content_hash
    _archive_dir_name = staticmethod(validation.archive_dir_name)
    _build_asset_key = staticmethod(policy.build_asset_key)
    _build_output_slug = staticmethod(policy.build_output_slug)
    _short_output_token = staticmethod(policy.short_output_token)
    _normalize_output_seed = staticmethod(policy.normalize_output_seed)
    _sanitize_output_fragment = staticmethod(policy.sanitize_output_fragment)
    _iter_output_candidates = staticmethod(policy.iter_output_candidates)
    _compute_hash = staticmethod(repository.compute_hash)
