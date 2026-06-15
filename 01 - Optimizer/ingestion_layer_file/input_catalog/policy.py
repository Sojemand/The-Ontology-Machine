"""Soft rules for filtering, ordering and state bootstrap policy."""
from __future__ import annotations

from pathlib import Path

from ..models import OutputFilters
from .types import CatalogEntry


def max_bytes_for_filters(filters: OutputFilters) -> int | None:
    if not filters.max_size_mb:
        return None
    return filters.max_size_mb * 1024 * 1024


def matches_filter(entry: CatalogEntry, filters: OutputFilters, max_bytes: int | None) -> bool:
    if filters.format and entry.extension.lower() != filters.format.lower():
        return False
    if filters.doc_type and filters.doc_type.lower() not in entry.filename.lower():
        return False
    if max_bytes is not None and entry.size_bytes > max_bytes:
        return False
    return True


def sort_entries(entries: list[CatalogEntry], processing_order: str) -> list[CatalogEntry]:
    ordered = list(entries)
    if processing_order == "format":
        ordered.sort(key=lambda entry: entry.extension.lower())
    elif processing_order == "size_asc":
        ordered.sort(key=lambda entry: entry.size_bytes)
    elif processing_order == "size_desc":
        ordered.sort(key=lambda entry: entry.size_bytes, reverse=True)
    return ordered


def should_bootstrap_outputs(
    state_path: Path | None,
    recovered_invalid_state: bool,
    hashes: set[str],
) -> bool:
    return bool(
        state_path
        and (
            not state_path.exists()
            or recovered_invalid_state
            or hashes
        )
    )
