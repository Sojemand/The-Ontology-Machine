"""Aggregated semantic corpus.db contract for evidence and materialization."""

from __future__ import annotations

from .schema_evidence import EVIDENCE_INDEXES, EVIDENCE_TABLES
from .schema_materialization import MATERIALIZATION_INDEXES, MATERIALIZATION_TABLES

SEMANTIC_TABLES = (*EVIDENCE_TABLES, *MATERIALIZATION_TABLES)
SEMANTIC_INDEXES = (*EVIDENCE_INDEXES, *MATERIALIZATION_INDEXES)
