"""CLI validation stage for hard boundary checks."""
from __future__ import annotations

from pathlib import Path


class CliUsageError(ValueError):
    """Raised when CLI arguments reference unusable paths."""


def require_structured_file(path: Path) -> Path:
    if not path.exists():
        raise CliUsageError(f"Structured JSON nicht gefunden: {path}")
    if not path.is_file():
        raise CliUsageError(f"Structured JSON muss eine Datei sein: {path}")
    return path


def require_structured_dir(path: Path) -> Path:
    if not path.is_dir():
        raise CliUsageError(f"Verzeichnis nicht gefunden: {path}")
    return path


def require_normalized_output_path(path: Path) -> Path:
    if path.exists() and path.is_dir():
        raise CliUsageError(f"normalized_output_path darf kein Verzeichnis sein: {path}")
    return path


def require_output_root(path: Path) -> Path:
    if path.exists() and not path.is_dir():
        raise CliUsageError(f"output_root muss ein Verzeichnis sein: {path}")
    return path


def require_worker_count(worker_count: int | None, max_batch_workers: int | None) -> int | None:
    if worker_count is None:
        return None
    if worker_count < 1:
        raise CliUsageError("Worker-Anzahl muss mindestens 1 sein.")
    if max_batch_workers is not None and worker_count > max_batch_workers:
        raise CliUsageError(f"Worker-Anzahl darf max_batch_workers ({max_batch_workers}) nicht ueberschreiten.")
    return worker_count


def require_batch_file_limit(path: Path, max_batch_files: int | None) -> None:
    if max_batch_files is None:
        return None
    count = 0
    for file_path in path.rglob("*.structured.json"):
        if not file_path.is_file():
            continue
        count += 1
        if count > max_batch_files:
            raise CliUsageError(f"Batch enthaelt mehr als max_batch_files ({max_batch_files}) Structured-Dateien.")
