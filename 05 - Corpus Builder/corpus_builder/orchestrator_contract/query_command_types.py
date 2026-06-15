"""Command dataclasses for query, export, and rebuild contract actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchCommand:
    corpus_db_path: str | None
    query: str
    mode: str
    limit: int | None = None
    runtime_model: str | None = None


@dataclass(frozen=True)
class StatsCommand:
    corpus_db_path: str | None = None


@dataclass(frozen=True)
class ExportCommand:
    corpus_db_path: str | None
    output_path: str
    fmt: str
    include_archived: bool = False


@dataclass(frozen=True)
class PreviewRebuildFromArtifactsCommand:
    pipeline_root: str | None = None
    normalized_dir: str | None = None
    structured_dir: str | None = None
    validation_dir: str | None = None
    raw_dir: str | None = None
    corpus_db_path: str | None = None
    release_path: str | None = None


@dataclass(frozen=True)
class RebuildFromArtifactsCommand(PreviewRebuildFromArtifactsCommand):
    replace_existing: bool = True


@dataclass(frozen=True)
class CreateAndRebuildNewCorpusDbCommand(PreviewRebuildFromArtifactsCommand):
    confirmation_artifact_path: str = ""
