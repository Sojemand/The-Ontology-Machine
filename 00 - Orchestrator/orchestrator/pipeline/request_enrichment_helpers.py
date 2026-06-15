"""Builder and path helpers for request enrichment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def build_source_from_doc(raw_doc: dict[str, Any], *, page_count: int) -> dict[str, Any]:
    return {
        "file_name": coerce_doc_text(raw_doc, "file_name", "filename"),
        "file_path": coerce_doc_text(raw_doc, "file_path", "path"),
        "file_ext": coerce_doc_text(raw_doc, "file_ext", "format"),
        "content_hash": str(raw_doc.get("content_hash", "")).strip(),
        "page_count": page_count,
        "document_type": coerce_doc_text(raw_doc, "document_type"),
        "language": coerce_doc_text(raw_doc, "language"),
        "size_bytes": raw_doc.get("size_bytes"),
        "created_at": raw_doc.get("created_at"),
        "modified_at": raw_doc.get("modified_at"),
        "is_scan": raw_doc.get("is_scan"),
        "has_handwriting": raw_doc.get("has_handwriting"),
    }


def coerce_page_asset(item: Any, *, page: int) -> dict[str, Any]:
    page_payload = required_mapping(item, "page_assets[]")
    path_text = str(page_payload.get("path", "")).strip()
    if not path_text:
        raise ValueError("page_assets[].path is missing.")
    return {
        "page": int(page_payload.get("page", page) or page),
        "path": path_text,
        "media_type": str(page_payload.get("media_type", "application/octet-stream")).strip() or "application/octet-stream",
        "format": page_payload.get("format"),
    }


def compact_page_asset(item: Any, *, page: int) -> dict[str, Any]:
    page_payload = required_mapping(item, "pages[]")
    path_text = str(page_payload.get("image_path", "")).strip()
    if not path_text:
        raise ValueError("pages[].image_path is missing.")
    media_type = str(page_payload.get("media_type", "")).strip()
    return {
        "page": int(page_payload.get("page", page) or page),
        "path": path_text,
        "media_type": media_type or None,
        "format": page_payload.get("format"),
    }


def required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    return value


def optional_mapping(value: Any) -> dict[str, Any]:
    return {} if value is None else required_mapping(value, "mapping")


def required_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    return value


def coerce_doc_text(raw_doc: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw_doc.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def relative_path_text(target_path: Path, request_parent: Path) -> str:
    return Path(os.path.relpath(Path(target_path), start=request_parent)).as_posix()
