"""Named handoff types for search validation, workflow, and scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreparedSqlStatement:
    statement: str
    masked_statement: str
    has_trailing_semicolon: bool


@dataclass(frozen=True)
class SearchFilter:
    key: str
    value: object


@dataclass
class HybridScoreEntry:
    document_id: str
    title: str | None
    description: str | None
    snippet: str | None
    fts: float = 0.0
    vec: float = 0.0
