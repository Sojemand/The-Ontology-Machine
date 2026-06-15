"""Batch limits, output path mapping, and fail-fast guards."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..document_io import budget_normalized_output_file_name
from ..models.results import NormalizationResult

SYSTEMIC_PROVIDER_ERROR_MARKERS = (
    "normalizer-llm-laeufe erfordern orchestrator-injizierte runtime-credentials",
    "orchestrator-api-key fehlt",
    "orchestrator-oauth fehlt",
    "provider nicht erreichbar",
    "provider timeout",
    "provider anfrage fehlgeschlagen",
    "provider api fehler 400",
    "provider api fehler 401",
    "provider api fehler 403",
    "provider api fehler 422",
    "provider api fehler 429",
    "provider api fehler 500",
    "provider api fehler 502",
    "provider api fehler 503",
    "provider api fehler 504",
)


def emit_progress(
    results: list[NormalizationResult],
    progress_callback: Callable[[NormalizationResult], None] | None,
) -> None:
    if not progress_callback:
        return
    for result in results:
        progress_callback(result)


def collect_batch_files(structured_dir: Path, max_batch_files: int) -> list[Path]:
    files: list[Path] = []
    for path in structured_dir.rglob("*.structured.json"):
        if not path.is_file():
            continue
        files.append(path)
        if len(files) > max_batch_files:
            raise ValueError(f"Batch enthaelt mehr als max_batch_files ({max_batch_files}) Structured-Dateien.")
    return sorted(files)


def resolve_worker_count(workers: int | None, default_workers: int, max_batch_workers: int) -> int:
    worker_count = max(1, workers or default_workers)
    if worker_count > max_batch_workers:
        raise ValueError(f"Worker-Anzahl darf max_batch_workers ({max_batch_workers}) nicht ueberschreiten.")
    return worker_count


def build_batch_output_path(structured_path: Path, *, structured_dir: Path, output_root: Path) -> Path:
    try:
        relative_parent = structured_path.relative_to(structured_dir).parent
    except ValueError as exc:
        raise ValueError(f"structured_path liegt ausserhalb des Batch-Roots: {structured_path}") from exc
    parent = output_root / relative_parent / "normalized"
    return parent / budget_normalized_output_file_name(parent, structured_path)


def mark_batch_aborted_if_systemic(result: NormalizationResult, *, remaining: int) -> bool:
    if result.status != "ERROR":
        return False
    message = result.message.casefold()
    if not any(marker in message for marker in SYSTEMIC_PROVIDER_ERROR_MARKERS):
        return False
    skipped = max(0, remaining)
    result.review_reason = "batch_fail_fast"
    result.message = f"Batch abgebrochen nach systemischem Provider-Fehler; {skipped} Dateien nicht gestartet. {result.message}"
    return True
