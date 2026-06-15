"""Workflow stage for corpus export orchestration."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Callable

from ..models.results import ExportResult
from . import adapter, domain, repository
from .types import ExportDocumentSnapshot

logger = logging.getLogger(__name__)


def export_jsonl(
    conn: sqlite3.Connection,
    output_path: Path,
    include_archived: bool = False,
) -> ExportResult:
    return _export_documents(
        conn,
        output_path,
        include_archived=include_archived,
        format_name="jsonl",
        transform=domain.build_jsonl_record,
        writer=adapter.write_jsonl,
    )


def export_csv(
    conn: sqlite3.Connection,
    output_path: Path,
    include_archived: bool = False,
) -> ExportResult:
    return _export_documents(
        conn,
        output_path,
        include_archived=include_archived,
        format_name="csv",
        transform=domain.build_csv_record,
        writer=adapter.write_csv,
    )


def _export_documents(
    conn: sqlite3.Connection,
    output_path: Path,
    *,
    include_archived: bool,
    format_name: str,
    transform: Callable[[ExportDocumentSnapshot], dict],
    writer: Callable[[Path, object], int],
) -> ExportResult:
    snapshots = repository.fetch_document_snapshots(
        conn,
        include_archived=include_archived,
    )
    resolved_output = adapter.prepare_output_path(output_path)
    logger.info(
        "%s-Export startet: %d Dokumente, include_archived=%s",
        format_name.upper(),
        len(snapshots),
        include_archived,
    )
    count = writer(resolved_output, (transform(snapshot) for snapshot in snapshots))
    logger.info(
        "%s-Export abgeschlossen: %d Dokumente nach %s",
        format_name.upper(),
        count,
        resolved_output,
    )
    return ExportResult(path=str(resolved_output), format=format_name, document_count=count)
