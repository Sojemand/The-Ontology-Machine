"""Thin public surface that keeps the historic import path stable."""
from __future__ import annotations

import threading
from pathlib import Path

from . import adapter, repository, validation, workflow
from .types import EMPTY_SNAPSHOT, CatalogEntry, CatalogSnapshot


class InputCatalog:
    _compute_hash = staticmethod(adapter.compute_hash)
    _is_valid_uuid_text = staticmethod(validation.is_valid_uuid_text)
    _normalize_hash_value = staticmethod(validation.normalize_hash_value)
    _read_hashes_from_file = staticmethod(repository.read_hashes_from_file)
    _serialize_hashes = staticmethod(repository.serialize_hashes)

    def __init__(
        self,
        input_dir: Path | None = None,
        *,
        state_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        self._path = Path(input_dir) if input_dir else None
        self._state_dir = Path(state_dir) if state_dir else None
        self._output_dir = Path(output_dir) if output_dir else None
        self._snapshot: CatalogSnapshot = EMPTY_SNAPSHOT
        self._processed_hashes: set[str] = set()
        self._state_lock = threading.RLock()

    @property
    def path(self) -> Path | None:
        return self._path

    @path.setter
    def path(self, value: Path | None):
        self._path = Path(value) if value else None
        self._reset_scan_state()

    @property
    def state_dir(self) -> Path | None:
        return self._state_dir

    @state_dir.setter
    def state_dir(self, value: Path | None):
        self._state_dir = Path(value) if value else None
        self._reset_scan_state()

    @property
    def output_dir(self) -> Path | None:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Path | None):
        self._output_dir = Path(value) if value else None
        self._reset_scan_state()

    def refresh(self) -> bool:
        self._reset_scan_state()
        if not self._path or not self._path.exists() or not self._path.is_dir():
            return False
        self._snapshot, self._processed_hashes = workflow.build_snapshot(
            self._path,
            self._state_dir,
            self._output_dir,
        )
        return True

    def iter_entries(self, offset: int = 0, limit: int = 50) -> list[CatalogEntry]:
        return list(self._snapshot.entries[offset:offset + limit])

    def iter_filtered(self, filters, processing_order: str = "input"):
        yield from workflow.iter_filtered_entries(self._snapshot.entries, filters, processing_order)

    def count_after_filter(self, filters) -> int:
        return workflow.count_filtered_entries(self._snapshot.entries, filters)

    def mark_processed_hash(self, content_hash: str) -> None:
        if not content_hash:
            return
        with self._state_lock:
            if content_hash in self._processed_hashes:
                return
            self._processed_hashes.add(content_hash)
            self._save_processed_hashes()

    def clear_processed_hashes(self) -> int:
        with self._state_lock:
            existing = self._read_hashes_from_state()
            self._processed_hashes = set()
            self._save_processed_hashes()
            return len(existing)

    def export_processed_hashes(self, target_path: Path) -> int:
        hashes = self._get_processed_hashes()
        repository.export_hashes(Path(target_path), hashes)
        return len(hashes)

    def import_processed_hashes(self, source_path: Path, replace: bool = True) -> int:
        imported = self._read_hashes_from_file(Path(source_path))
        with self._state_lock:
            if replace:
                self._processed_hashes = set(imported)
            else:
                current = self._get_processed_hashes()
                current.update(imported)
                self._processed_hashes = current
            self._save_processed_hashes()
            return len(self._processed_hashes)

    @property
    def total_count(self) -> int:
        return self._snapshot.total_count

    @property
    def summary(self) -> dict[str, int]:
        return dict(self._snapshot.summary)

    @property
    def total_size(self) -> int:
        return self._snapshot.total_size

    @property
    def loaded(self) -> bool:
        return self._snapshot.loaded

    @property
    def skipped_processed_count(self) -> int:
        return self._snapshot.skipped_processed_count

    @property
    def skipped_duplicate_count(self) -> int:
        return self._snapshot.skipped_duplicate_count

    @property
    def processed_hash_count(self) -> int:
        return len(self._get_processed_hashes())

    @property
    def processed_hashes_path(self) -> Path | None:
        return self._processed_hashes_path()

    def _load_processed_hashes(self) -> set[str]:
        self._processed_hashes = workflow.load_processed_hashes(self._state_dir, self._output_dir)
        return set(self._processed_hashes)

    def _save_processed_hashes(self) -> None:
        repository.save_processed_hashes(self._state_dir, self._processed_hashes)

    def _processed_hashes_path(self) -> Path | None:
        return repository.processed_hashes_path(self._state_dir)

    def _get_processed_hashes(self) -> set[str]:
        with self._state_lock:
            if self._processed_hashes:
                return set(self._processed_hashes)
            state_hashes = self._read_hashes_from_state()
            if state_hashes:
                self._processed_hashes = set(state_hashes)
                return set(self._processed_hashes)
        return self._load_processed_hashes()

    def _read_hashes_from_state(self) -> set[str]:
        return repository.read_hashes_from_state(self._state_dir)

    def _read_hashes_from_state_with_status(self) -> tuple[set[str], bool]:
        return repository.read_hashes_from_state_with_status(self._state_dir)

    def _collect_existing_output_hashes(self) -> set[str]:
        return adapter.collect_existing_output_hashes(self._output_dir)

    def _completed_output_hash(self, raw_file: Path) -> str | None:
        return adapter.completed_output_hash(Path(raw_file))

    def _iter_input_files(self):
        return adapter.iter_input_files(self._path, self._output_dir, self._state_dir)

    def _reset_scan_state(self) -> None:
        self._snapshot = EMPTY_SNAPSHOT
