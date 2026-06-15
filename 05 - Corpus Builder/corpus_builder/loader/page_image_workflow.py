"""Workflow seam for optional, blob-separated page image persistence."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from . import page_image_adapter, page_image_repository

logger = logging.getLogger(__name__)


def persist_document_page_images(
    conn: sqlite3.Connection,
    document_id: str,
    document: dict[str, object],
    *,
    enabled: bool,
    page_images_dir: str | Path | None,
    artifact_hint_path: Path | None,
    max_image_bytes: int | None = 10485760,
    max_total_bytes: int | None = 104857600,
) -> int:
    if not enabled:
        return 0
    page_images, warnings = page_image_adapter.load_page_images(
        document,
        page_images_dir=page_images_dir,
        artifact_hint_path=artifact_hint_path,
        max_image_bytes=max_image_bytes,
        max_total_bytes=max_total_bytes,
    )
    for warning in warnings:
        logger.warning("Seitenbild-Persistenz %s: %s", document_id, warning)
    page_image_repository.replace_page_images(conn, document_id, page_images)
    return len(page_images)


__all__ = ["persist_document_page_images"]
