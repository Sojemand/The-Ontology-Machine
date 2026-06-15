"""Workflow surface for the odt-odfpy extractor."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from . import adapter, domain, validation
from .types import OdtProjection, OdtStageError

_VERSION = "1.0.0"


def extract(input_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    del config
    start = time.perf_counter_ns()
    try:
        source = validation.validate_source(input_path)
        snapshot = adapter.load_document_snapshot(source)
        projection = domain.project_document(snapshot)
        return _success_envelope(projection, start)
    except OdtStageError as exc:
        return _error_envelope(start, str(exc))
    except Exception as exc:
        return _error_envelope(start, f"workflow.extract: {exc}")


def selftest() -> dict[str, Any]:
    try:
        adapter.ensure_odfpy()
    except OdtStageError as exc:
        return {"status": "error", "version": _VERSION, "error": exc.detail}
    return {"status": "ok", "version": _VERSION}


def _success_envelope(projection: OdtProjection, start: int) -> dict[str, Any]:
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
