"""Workflow stage for assembling corpus stats reports."""

from __future__ import annotations

import sqlite3
from typing import cast

from . import repository
from .types import CorpusStats


def corpus_stats(conn: sqlite3.Connection) -> CorpusStats:
    overview = repository.fetch_overview(conn)
    total_documents = int(overview["total_documents"])
    return cast(
        CorpusStats,
        {
            **overview,
            **repository.fetch_document_groups(conn),
            "by_entity_type": repository.fetch_entity_type_counts(conn),
            **repository.fetch_top_rankings(conn),
            **repository.fetch_numeric_stats(conn, total_documents=total_documents),
        },
    )
