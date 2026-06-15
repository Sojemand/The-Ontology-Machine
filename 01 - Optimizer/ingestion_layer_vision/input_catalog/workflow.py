"""Visible refresh pipeline: load state, bootstrap, walk input, dedupe, snapshot."""
from __future__ import annotations

import logging
from pathlib import Path

from ..models import OutputFilters
from . import adapter, policy, repository
from .types import CatalogEntry, CatalogSnapshot

logger = logging.getLogger(__name__)


def load_processed_hashes(state_dir: Path | None, output_dir: Path | None) -> set[str]:
    state_path = repository.processed_hashes_path(state_dir)
    hashes, recovered_invalid_state = repository.read_hashes_from_state_with_status(state_dir)
    if policy.should_bootstrap_outputs(state_path, recovered_invalid_state, hashes):
        bootstrap_hashes = adapter.collect_existing_output_hashes(output_dir)
        missing_hashes = bootstrap_hashes.difference(hashes)
        if missing_hashes or recovered_invalid_state:
            hashes.update(missing_hashes)
            repository.save_processed_hashes(state_dir, hashes)
    return set(hashes)


def build_snapshot(
    input_dir: Path,
    state_dir: Path | None,
    output_dir: Path | None,
) -> tuple[CatalogSnapshot, set[str]]:
    processed_hashes = load_processed_hashes(state_dir, output_dir)
    seen_hashes: set[str] = set()
    entries: list[CatalogEntry] = []
    summary: dict[str, int] = {}
    total_size = 0
    skipped_processed_count = 0
    skipped_duplicate_count = 0

    for file_path in adapter.iter_input_files(input_dir, output_dir, state_dir):
        stat_result = _safe_stat(file_path)
        if stat_result is None:
            continue

        content_hash = adapter.compute_hash(file_path)
        stat_result = _safe_stat(file_path)
        if stat_result is None:
            continue
        if content_hash and content_hash in processed_hashes:
            skipped_processed_count += 1
            continue
        if content_hash and content_hash in seen_hashes:
            skipped_duplicate_count += 1
            continue
        if content_hash:
            seen_hashes.add(content_hash)

        entry = adapter.build_catalog_entry(
            file_path,
            stat_result,
            input_root=Path(input_dir),
            content_hash=content_hash,
        )
        entries.append(entry)
        summary[entry.extension] = summary.get(entry.extension, 0) + 1
        total_size += entry.size_bytes

    snapshot = CatalogSnapshot(
        entries=tuple(entries),
        summary=summary,
        total_size=total_size,
        skipped_processed_count=skipped_processed_count,
        skipped_duplicate_count=skipped_duplicate_count,
        loaded=True,
    )
    return snapshot, processed_hashes


def _safe_stat(file_path: Path):
    try:
        return file_path.stat()
    except OSError as exc:
        logger.warning("Input-Datei konnte nicht gelesen werden: %s (%s)", file_path, exc)
    return None


def _collect_filtered_entries(entries: tuple[CatalogEntry, ...], filters: OutputFilters) -> list[CatalogEntry]:
    max_bytes = policy.max_bytes_for_filters(filters)
    matched: list[CatalogEntry] = []
    for entry in entries:
        if filters.batch_size and len(matched) >= filters.batch_size:
            break
        if policy.matches_filter(entry, filters, max_bytes):
            matched.append(entry)
    return matched


def iter_filtered_entries(
    entries: tuple[CatalogEntry, ...],
    filters: OutputFilters,
    processing_order: str = "input",
):
    yield from policy.sort_entries(_collect_filtered_entries(entries, filters), processing_order)


def count_filtered_entries(entries: tuple[CatalogEntry, ...], filters: OutputFilters) -> int:
    return len(_collect_filtered_entries(entries, filters))
