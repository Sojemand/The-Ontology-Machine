"""Path-stable surface for corpus loader helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from . import repository as _repository
from . import workflow as _workflow
from .policy import detect_field_type


def _insert_fts_entry(
    conn: sqlite3.Connection,
    doc_id: str,
    doc: dict[str, Any],
    fields: dict[str, Any],
    rows: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    tags: list[str],
    people: list[str],
    orgs: list[str],
    promotions: list[dict[str, Any]] | None = None,
) -> None:
    _repository.insert_fts_entry(conn, doc_id, doc, fields, rows, segments, tags, people, orgs, promotions)


def load_document(
    conn: sqlite3.Connection,
    document_id: str,
    structured_json: dict[str, Any] | None,
    validation_report: dict[str, Any] | None,
    content_hash: str,
    file_path: str,
    normalized_json: dict[str, Any] | None = None,
    semantic_release: dict[str, Any] | None = None,
    *,
    raw_json: dict[str, Any] | None = None,
    persist_page_images_in_db: bool = False,
    page_images_dir: str | Path | None = None,
    persist_original_artifact_in_db: bool = False,
    max_original_artifact_bytes: int | None = 52428800,
    max_page_image_bytes: int | None = 10485760,
    max_page_image_total_bytes: int | None = 104857600,
    artifact_hint_path: Path | None = None,
):
    return _workflow.load_document(
        conn,
        document_id,
        structured_json,
        validation_report,
        content_hash,
        file_path,
        normalized_json,
        raw_json=raw_json,
        semantic_release=semantic_release,
        insert_fts_entry_fn=_insert_fts_entry,
        persist_page_images_in_db=persist_page_images_in_db,
        page_images_dir=page_images_dir,
        persist_original_artifact_in_db=persist_original_artifact_in_db,
        max_original_artifact_bytes=max_original_artifact_bytes,
        max_page_image_bytes=max_page_image_bytes,
        max_page_image_total_bytes=max_page_image_total_bytes,
        artifact_hint_path=artifact_hint_path,
    )


def load_from_file(
    conn: sqlite3.Connection,
    normalized_path: Path,
    validation_path: Path | None,
    *,
    structured_path: Path | None = None,
    raw_path: Path | None = None,
    semantic_release: dict[str, Any] | None = None,
    persist_page_images_in_db: bool = False,
    page_images_dir: str | Path | None = None,
    persist_original_artifact_in_db: bool = False,
    max_original_artifact_bytes: int | None = 52428800,
    max_page_image_bytes: int | None = 10485760,
    max_page_image_total_bytes: int | None = 104857600,
):
    return _workflow.load_from_file(
        conn,
        normalized_path,
        validation_path,
        structured_path=structured_path,
        raw_path=raw_path,
        semantic_release=semantic_release,
        insert_fts_entry_fn=_insert_fts_entry,
        persist_page_images_in_db=persist_page_images_in_db,
        page_images_dir=page_images_dir,
        persist_original_artifact_in_db=persist_original_artifact_in_db,
        max_original_artifact_bytes=max_original_artifact_bytes,
        max_page_image_bytes=max_page_image_bytes,
        max_page_image_total_bytes=max_page_image_total_bytes,
    )


def rematerialize_document(conn: sqlite3.Connection, document_id: str, semantic_release: dict[str, Any]):
    return _workflow.rematerialize_document(conn, document_id, semantic_release)


__all__ = ["detect_field_type", "load_document", "load_from_file", "rematerialize_document"]
