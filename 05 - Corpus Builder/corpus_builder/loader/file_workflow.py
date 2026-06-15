"""File-bundle entry point for corpus loader workflow."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Callable

from ..models.results import LoadResult
from . import adapter, repository
from .document_workflow import load_document
from .types import JsonDict

logger = logging.getLogger(__name__)


def load_from_file(
    conn: sqlite3.Connection,
    normalized_path: Path,
    validation_path: Path | None,
    *,
    structured_path: Path | None = None,
    raw_path: Path | None = None,
    semantic_release: JsonDict | None = None,
    insert_fts_entry_fn: Callable[..., None] = repository.insert_fts_entry,
    persist_page_images_in_db: bool = False,
    page_images_dir: str | Path | None = None,
    persist_original_artifact_in_db: bool = False,
    max_original_artifact_bytes: int | None = 52428800,
    max_page_image_bytes: int | None = 10485760,
    max_page_image_total_bytes: int | None = 104857600,
) -> LoadResult:
    normalized_file = Path(normalized_path)
    structured_file = Path(structured_path) if structured_path is not None else None
    document_id = adapter.derive_document_id(normalized_file)
    try:
        bundle = adapter.load_bundle(normalized_file, validation_path, structured_path=structured_file, raw_path=raw_path)
    except Exception as exc:
        logger.error("Fehler beim Laden aus Datei %s: %s", normalized_file, exc)
        return LoadResult(status="error", document_id=document_id, reason=str(exc))
    return load_document(
        conn,
        bundle.document_id,
        bundle.structured_json,
        bundle.validation_report,
        bundle.content_hash,
        bundle.file_path,
        bundle.normalized_json,
        raw_json=bundle.raw_json,
        semantic_release=semantic_release,
        insert_fts_entry_fn=insert_fts_entry_fn,
        persist_page_images_in_db=persist_page_images_in_db,
        page_images_dir=page_images_dir,
        persist_original_artifact_in_db=persist_original_artifact_in_db,
        max_original_artifact_bytes=max_original_artifact_bytes,
        max_page_image_bytes=max_page_image_bytes,
        max_page_image_total_bytes=max_page_image_total_bytes,
        artifact_hint_path=normalized_file,
    )


__all__ = ["load_from_file"]
