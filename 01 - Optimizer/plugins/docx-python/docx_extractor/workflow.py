"""Workflow surface for the docx-python extractor."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from . import adapter, domain, validation
from .types import PreparedSource, WordProjection, WordStageError

_VERSION = "1.0.0"


def extract(input_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    start = time.perf_counter_ns()
    prepared: PreparedSource | None = None
    config_data = dict(config or {})
    try:
        source = validation.validate_source(input_path)
        prepared = adapter.prepare_source(source, config_data)
        snapshot = adapter.load_document_snapshot(prepared.source, config_data)
        projection = domain.project_document(snapshot)
        return _success_envelope(projection, start)
    except WordStageError as exc:
        return _error_envelope(start, str(exc))
    except Exception as exc:
        return _error_envelope(start, f"workflow.extract: {exc}")
    finally:
        adapter.cleanup_prepared_source(prepared)


def selftest() -> dict[str, Any]:
    try:
        adapter.ensure_python_docx()
    except WordStageError as exc:
        return {"status": "error", "version": _VERSION, "error": exc.detail}
    return {"status": "ok", "version": _VERSION}


def _success_envelope(projection: WordProjection, start: int) -> dict[str, Any]:
    return {
        "status": "success",
        "blocks": projection.blocks,
        "metadata": projection.metadata,
        "errors": [],
        "processing_time_ms": _elapsed_ms(start),
    }


def _error_envelope(start: int, error: str) -> dict[str, Any]:
    return {
        "status": "error",
        "blocks": [],
        "metadata": {},
        "errors": [error],
        "processing_time_ms": _elapsed_ms(start),
    }


def _elapsed_ms(start: int) -> int:
    return (time.perf_counter_ns() - start) // 1_000_000
