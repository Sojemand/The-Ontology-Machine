"""Path-stable surface for corpus stats and reporting."""

from __future__ import annotations

from .adapter import format_stats, print_stats
from .types import CorpusDateRange, CorpusStats
from .workflow import corpus_stats

__all__ = [
    "CorpusDateRange",
    "CorpusStats",
    "corpus_stats",
    "format_stats",
    "print_stats",
]
