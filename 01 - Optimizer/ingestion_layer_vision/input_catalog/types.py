"""Named contracts for the staged input catalog pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CatalogEntry:
    path: Path
    filename: str
    extension: str
    size_bytes: int
    created: str
    modified: str
    relative_path: str
    content_hash: str = ""


@dataclass(frozen=True)
class CatalogSnapshot:
    entries: tuple[CatalogEntry, ...] = ()
    summary: dict[str, int] = field(default_factory=dict)
    total_size: int = 0
    skipped_processed_count: int = 0
    skipped_duplicate_count: int = 0
    loaded: bool = False

    @property
    def total_count(self) -> int:
        return len(self.entries)


EMPTY_SNAPSHOT = CatalogSnapshot()
