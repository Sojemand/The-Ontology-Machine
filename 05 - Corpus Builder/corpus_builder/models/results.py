"""Named result types for Corpus Builder workflow outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadResult:
    status: str = ""
    document_id: str = ""
    reason: str | None = None


@dataclass
class SearchResult:
    document_id: str = ""
    title: str | None = None
    description: str | None = None
    snippet: str | None = None
    score: float = 0.0
    source: str = "fts"


@dataclass
class ExportResult:
    path: str = ""
    format: str = ""
    document_count: int = 0


@dataclass
class LoadBatchResult:
    loaded: int = 0
    skipped: int = 0
    archived: int = 0
    errors: int = 0
    results: list[LoadResult] = field(default_factory=list)


@dataclass
class EmbeddingRunResult:
    status: str = ""
    count: int = 0
    reason: str | None = None
