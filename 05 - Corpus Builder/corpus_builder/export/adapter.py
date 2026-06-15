"""File I/O adapter stage for corpus export outputs."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable

from ..models.serialization import atomic_file_write
from .types import CSV_FIELDNAMES

logger = logging.getLogger(__name__)


def prepare_output_path(output_path: Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0

    def _write(tmp_path: Path) -> None:
        nonlocal count
        with tmp_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    atomic_file_write(path, _write)
    logger.info("JSONL-Datei geschrieben: %d Dokumente nach %s", count, path)
    return count


def write_csv(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0

    def _write(tmp_path: Path) -> None:
        nonlocal count
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow(record)
                count += 1

    atomic_file_write(path, _write)
    logger.info("CSV-Datei geschrieben: %d Dokumente nach %s", count, path)
    return count
